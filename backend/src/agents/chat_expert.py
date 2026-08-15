"""Chat Expert Agent — multi-module conversational explainer.

Supports six modules:
  - small_claims
  - criminal_procedure
  - police_report
  - discovery_motion
  - property_casualty
  - wills_trusts

Each module has a strict system prompt that:
  1. Gives educated legal answers — tells people what they should do
  2. Frames answers as expert guidance, not just information
  3. Rejects off-topic questions
  4. Ends every response directing to a licensed Florida attorney

Uses claude-sonnet-4-6 via the existing AsyncAnthropic client.
Streams responses as SSE text chunks.
"""

import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.url_filter import StreamingURLFilter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

VALID_MODULES = frozenset({
    "small_claims",
    "criminal_procedure",
    "police_report",
    "discovery_motion",
    "property_casualty",
    "wills_trusts",
})

MODULE_LABELS: dict[str, str] = {
    "small_claims": "small claims court",
    "criminal_procedure": "criminal procedure",
    "police_report": "police reports and criminal procedure",
    "discovery_motion": "discovery rules and motions",
    "property_casualty": "property and casualty law",
    "wills_trusts": "wills, trusts, and probate",
}

# ---------------------------------------------------------------------------
# Max free messages before paywall
# ---------------------------------------------------------------------------

MAX_FREE_MESSAGES = 5


# ---------------------------------------------------------------------------
# System prompts — one per module
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS: dict[str, str] = {
    "small_claims": (
        "You are a Florida small claims court expert. Answer ONLY "
        "questions about FL small claims: jurisdiction up to $8,000, "
        "filing procedures, typical timelines, hearings, documentation, "
        "outcomes. Frame all answers educationally: 'Typically...', "
        "'In most cases...', 'Research shows...'. Third-person framing. "
        "No 'you should' / 'you must'. Help users understand what "
        "usually happens so they can make informed decisions. If asked "
        "anything outside small claims — respond exactly: 'I can only "
        "answer questions about small claims court in Florida.' "
        "End every response with the required disclaimer."
    ),
    "criminal_procedure": (
        "You are a Florida criminal procedure expert. Answer ONLY "
        "questions about FL criminal process: arrest, charging, "
        "arraignment, bail/bond, public defenders, plea deals, trial, "
        "sentencing. For plea deals — explain what typically happens "
        "for specific charges in Florida, typical outcomes for similar "
        "cases, what factors courts usually consider. Frame as "
        "educational research: 'In most FL criminal cases...', "
        "'Research on similar charges shows...', 'Courts typically...'. "
        "Third-person only. Never direct the user. Help them understand "
        "their situation so they can make informed decisions with their "
        "attorney. If asked anything outside criminal procedure — "
        "respond exactly: 'I can only answer questions about criminal "
        "procedure in Florida.' End every response with the required "
        "disclaimer."
    ),
    "police_report": (
        "You are a Florida police report analysis expert. Answer ONLY "
        "questions about: what charges mean, Miranda rights, probable "
        "cause, how reports are used in court, what discrepancies "
        "matter, constitutional issues in police procedures. Frame as "
        "education: 'Courts typically view...', 'Constitutional law "
        "provides...'. Third-person only. Never tell them to take "
        "action. If asked anything outside police reports — respond "
        "exactly: 'I can only answer questions about police reports "
        "and arrest procedures.' End every response with the required "
        "disclaimer."
    ),
    "discovery_motion": (
        "You are a Florida discovery procedure expert. Answer ONLY "
        "questions about FL Rule 3.220 discovery: what must be "
        "produced, timelines, Brady violations, Giglio issues, what "
        "happens if discovery is not provided. Frame as legal "
        "education: 'FL Rule 3.220 requires...', 'Courts typically "
        "find...'. Third-person only. If asked anything outside "
        "discovery — respond exactly: 'I can only answer questions "
        "about Florida discovery rules.' End every response with "
        "the required disclaimer."
    ),
    "property_casualty": (
        "You are a Florida property and casualty law expert. Answer "
        "ONLY questions about: insurance bad faith under FL 624.155, "
        "premises liability under FL 768.0755, comparative negligence, "
        "duty of care, typical settlement ranges, documentation needed. "
        "Frame as research: 'In typical FL P&C cases...', 'Florida law "
        "generally requires...'. Third-person only. If asked anything "
        "outside P&C — respond exactly: 'I can only answer questions "
        "about Florida property and casualty law.' End every response "
        "with the required disclaimer."
    ),
    "wills_trusts": (
        "You are a Florida wills, trusts, and probate expert. Answer "
        "ONLY questions about FL wills, trusts, probate, estate "
        "planning, executors, trustees, beneficiaries, Lady Bird "
        "deeds, small estate affidavits. If asked anything outside "
        "this scope — respond exactly: 'I can only answer questions "
        "about wills, trusts, and probate in Florida.' Third-person "
        "only. End every response with the required disclaimer."
    ),
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ChatExpertAgent:
    """Streaming conversational agent for LegalClear explainer modules."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    # ── public API ─────────────────────────────────────────────────────

    async def chat(
        self,
        module: str,
        message: str,
        session_id: str,
        language: str = "en",
        chat_history: list[dict] | None = None,
        message_count: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Stream a per-module conversational response.

        Parameters
        ----------
        module :
            One of VALID_MODULES.
        message :
            The user's latest question.
        session_id :
            Opaque session identifier (logged for debugging).
        language :
            en or es — controls the disclaimer language only.
        chat_history :
            Optional list of prior {role, content} dicts for context.
        message_count :
            Number of messages already sent in this session (before this one).
            If >= MAX_FREE_MESSAGES, a paywall SSE is yielded instead.
        """

        # ── Paywall check ──────────────────────────────────────────
        # Skipped entirely when PAYMENTS_ENABLED is off — chat is free.
        if settings.PAYMENTS_ENABLED and message_count >= MAX_FREE_MESSAGES:
            paywall_payload = json.dumps({
                "paywall": True,
                "message": "You've used all 5 expert questions. Unlock unlimited questions for $9.99.",
            })
            yield f"data: {paywall_payload}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        if module not in SYSTEM_PROMPTS:
            error_payload = json.dumps({
                "error": True,
                "message": f"Unknown module: {module}",
                "disclaimer": get_disclaimer(language),
            })
            yield f"data: {error_payload}\n\n"
            return

        system_prompt = SYSTEM_PROMPTS[module]
        disclaimer = get_disclaimer(language)

        # ── Build messages array ───────────────────────────────────
        messages: list[dict] = []

        # Include prior chat history for context
        if chat_history:
            for entry in chat_history:
                role = entry.get("role", "user")
                content = entry.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        url_filter = StreamingURLFilter(f"chat_expert:{module}")
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=messages,
            ) as stream:
                async for chunk in stream.text_stream:
                    safe = url_filter.feed(chunk)
                    if safe:
                        yield f"data: {json.dumps({'chunk': safe})}\n\n"
                tail = url_filter.flush()
                if tail:
                    yield f"data: {json.dumps({'chunk': tail})}\n\n"

                # Append disclaimer as final chunk
                yield f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
                # Signal end of stream
                yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception:
            logger.error(
                "ChatExpertAgent stream error for module=%s session=%s:\n%s",
                module,
                session_id,
                traceback.format_exc(),
            )
            error_payload = json.dumps({
                "error": True,
                "message": "Response could not be generated. Please try again.",
                "disclaimer": disclaimer,
            })
            yield f"data: {error_payload}\n\n"
