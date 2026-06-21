"""Chat Expert Agent — multi-module conversational explainer.

Supports five modules:
  - small_claims
  - criminal_procedure
  - police_report
  - discovery_motion
  - property_casualty

Each module has a strict system prompt that:
  1. Uses third-person framing only
  2. Never says "you should" / "you must" / "you need to"
  3. Frames answers as education/research
  4. Rejects off-topic questions
  5. Appends the LegalClear disclaimer

Uses claude-sonnet-4-6 via the existing AsyncAnthropic client.
Streams responses as SSE text chunks.
"""

import json
import logging
import traceback
from typing import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer

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
})

MODULE_LABELS: dict[str, str] = {
    "small_claims": "small claims court",
    "criminal_procedure": "criminal procedure",
    "police_report": "police reports and criminal procedure",
    "discovery_motion": "discovery rules and motions",
    "property_casualty": "property and casualty law",
}

# ---------------------------------------------------------------------------
# System prompts — one per module
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS: dict[str, str] = {
    "small_claims": (
        "You are a Florida small claims court expert advisor. Your role "
        "is to help non-lawyers understand small claims court in plain "
        "English. Answer ONLY questions about: Florida small claims "
        "jurisdiction (up to $8,000), filing procedures, typical "
        "timelines, documentation needed, what judges typically look for, "
        "common outcomes, how to prepare for hearing.\n\n"
        "REJECT off-topic questions with: 'I can only answer questions "
        "about Florida small claims court.'\n\n"
        "Frame all answers educationally: 'In most cases...', "
        "'Typically...', 'Research shows...'. Never direct the user "
        "what to do. Help them understand what usually happens so they "
        "can make informed decisions. Include disclaimer at the end of "
        "every response."
    ),
    "criminal_procedure": (
        "You are a Florida criminal procedure expert advisor. Your role "
        "is to help non-lawyers understand the Florida criminal justice "
        "process in plain English. Answer ONLY questions about: Florida "
        "criminal procedure stages, what typically happens at each stage, "
        "typical plea deal structures for different charges in Florida, "
        "bond hearings, public defender role, discovery rights under "
        "FL Rule 3.220, sentencing guidelines, what similar cases "
        "typically result in.\n\n"
        "REJECT off-topic questions with: 'I can only answer questions "
        "about Florida criminal procedure.'\n\n"
        "Frame all answers educationally: 'In most criminal cases...', "
        "'Typically in Florida...', 'Research on similar charges shows...'. "
        "Never direct the user what to do. Help them research and "
        "understand their situation so they can make informed decisions "
        "with their attorney. Include disclaimer at end."
    ),
    "police_report": (
        "You are a Florida police report analysis expert. Your role is "
        "to help non-lawyers understand what's in a police report and "
        "what it typically means. Answer ONLY questions about: what "
        "different charges mean, Miranda rights and what they mean, "
        "probable cause statements, how police reports are used in court, "
        "what discrepancies matter, what evidence officers typically cite, "
        "constitutional issues in police procedures.\n\n"
        "REJECT off-topic questions with: 'I can only answer questions "
        "about police reports and criminal procedure.'\n\n"
        "Frame answers as research and education: 'Courts typically view...', "
        "'In most cases...', 'Constitutional law provides...'. Never tell "
        "them to challenge evidence or take action. Help them understand "
        "what the report says so they can discuss it with their attorney. "
        "Include disclaimer at end."
    ),
    "discovery_motion": (
        "You are a Florida discovery and criminal procedure expert. Your "
        "role is to help non-lawyers understand discovery rules and "
        "motions. Answer ONLY questions about: FL Rule of Criminal "
        "Procedure 3.220 discovery obligations, what prosecutors must "
        "produce, what defendants have the right to, motion filing "
        "procedures, typical timelines, what happens if discovery isn't "
        "provided, Brady violations, Giglio issues.\n\n"
        "REJECT off-topic questions with: 'I can only answer questions "
        "about Florida discovery rules and motions.'\n\n"
        "Frame as legal education: 'FL Rule 3.220 requires...', "
        "'Typically prosecutors must provide...', 'In most cases courts "
        "find...'. Never direct action. Help them understand their rights "
        "and what usually happens. Include disclaimer at end."
    ),
    "property_casualty": (
        "You are a Florida property and casualty law expert. Your role "
        "is to help non-lawyers understand property and casualty cases. "
        "Answer ONLY questions about: insurance bad faith under FL 624.155, "
        "premises liability and duty of care, comparative negligence in FL, "
        "typical settlement ranges, what documentation is relevant, "
        "insurance policy interpretation, what courts typically award.\n\n"
        "REJECT off-topic questions with: 'I can only answer questions "
        "about Florida property and casualty law.'\n\n"
        "Frame as research and education: 'In typical P&C cases...', "
        "'Florida law generally requires...', 'Research shows most "
        "settlements...'. Help them understand typical outcomes and what "
        "evidence matters. Include disclaimer at end."
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
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response as SSE text chunks.

        Args:
            module: One of small_claims, criminal_procedure, police_report,
                    discovery_motion, property_casualty.
            message: The user's question.
            session_id: Chat session identifier (opaque to the agent).
            language: 'en' or 'es'.

        Yields:
            SSE-formatted strings: ``data: {chunk}\\n\\n``
        """
        if module not in VALID_MODULES:
            error_payload = json.dumps({
                "error": True,
                "message": f"Unknown module: {module}",
                "disclaimer": get_disclaimer(language),
            })
            yield f"data: {error_payload}\n\n"
            return

        system_prompt = SYSTEM_PROMPTS[module]
        disclaimer = get_disclaimer(language)

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": message}],
            ) as stream:
                async for chunk in stream.text_stream:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

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
