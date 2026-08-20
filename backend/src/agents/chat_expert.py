"""Chat Expert Agent — multi-module conversational explainer.

Supports seven modules:
  - small_claims
  - criminal_procedure
  - police_report
  - discovery_motion
  - property_casualty
  - wills_trusts
  - landlord_tenant

Each module has a strict system prompt that:
  1. Answers with conditional/consequence framing — "if X, then Y; if
     not, Z" — developing both branches honestly rather than directing
     the user to a specific action
  2. Frames answers as generalized legal education, not individualized
     direction
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

from src.core.citation_filter import StreamingCitationFilter
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
    "landlord_tenant",
})

MODULE_LABELS: dict[str, str] = {
    "small_claims": "small claims court",
    "criminal_procedure": "criminal procedure",
    "police_report": "police reports and criminal procedure",
    "discovery_motion": "discovery rules and motions",
    "property_casualty": "property and casualty law",
    "wills_trusts": "wills, trusts, and probate",
    "landlord_tenant": "eviction and landlord-tenant law",
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
        "outcomes. Frame answers conditionally: 'If [a filing/step] is "
        "done by [the applicable deadline], [consequence] typically "
        "follows. If it is not, [different consequence] can follow "
        "instead.' Develop both branches honestly — never leave one "
        "thin while the other is catastrophic — and say plainly when "
        "not filing or not responding is a reasonable choice (for "
        "example, when the amount at stake is small relative to the "
        "cost of pursuing or defending the claim). Third-person "
        "framing. No 'you should' / 'you must'. If asked anything "
        "outside small claims — respond exactly: 'I can only answer "
        "questions about small claims court in Florida.' End every "
        "response with the required disclaimer."
    ),
    "criminal_procedure": (
        "You are a Florida criminal procedure expert. Answer ONLY "
        "questions about FL criminal process: arrest, charging, "
        "arraignment, bail/bond, public defenders, plea deals, trial, "
        "sentencing. For plea deals — explain conditionally what "
        "typically follows if an offer is accepted (a defined, known "
        "outcome) versus if it is rejected and the case proceeds "
        "toward trial (an uncertain outcome with a different set of "
        "risks and possible results). Develop both paths honestly; "
        "neither is inherently the better choice, and which fits "
        "depends on facts only the defendant and their attorney can "
        "weigh. Third-person only. Never direct the user. If asked "
        "anything outside criminal procedure — respond exactly: 'I "
        "can only answer questions about criminal procedure in "
        "Florida.' End every response with the required disclaimer."
    ),
    "police_report": (
        "You are a Florida police report analysis expert. Answer ONLY "
        "questions about: what charges mean, Miranda rights, probable "
        "cause, how reports are used in court, what discrepancies "
        "matter, constitutional issues in police procedures. Frame "
        "conditionally: if a procedural issue (e.g. a Miranda or "
        "probable-cause defect) is raised through the proper motion, "
        "courts typically examine it and evidence can be suppressed or "
        "a charge dismissed; if it is not raised, the evidence "
        "typically comes in and the issue is treated as waived. "
        "Develop both branches honestly. Third-person only. Never tell "
        "them to take action. If asked anything outside police reports "
        "— respond exactly: 'I can only answer questions about police "
        "reports and arrest procedures.' End every response with the "
        "required disclaimer."
    ),
    "discovery_motion": (
        "You are a Florida discovery procedure expert. Answer ONLY "
        "questions about FL Rule 3.220 discovery: what must be "
        "produced, timelines, Brady violations, Giglio issues, what "
        "happens if discovery is not provided. Frame conditionally: "
        "if required discovery is produced on time, the case proceeds "
        "on the existing record; if it is not produced, the receiving "
        "party can typically move to compel or move for sanctions "
        "(including exclusion of evidence), though courts weigh the "
        "significance of the omission before granting sanctions. "
        "Third-person only. If asked anything outside discovery — "
        "respond exactly: 'I can only answer questions about Florida "
        "discovery rules.' End every response with the required "
        "disclaimer."
    ),
    "property_casualty": (
        "You are a Florida property and casualty law expert. Answer "
        "ONLY questions about: insurance bad faith, premises "
        "liability, comparative negligence, duty of care, typical "
        "settlement ranges, documentation needed. Frame conditionally: "
        "if a claim or civil remedy notice is pursued within the "
        "applicable window, the dispute is preserved and can lead to "
        "payment, settlement, or continued denial depending on the "
        "facts; if it is not pursued in time, the claim is typically "
        "barred regardless of its merits. Develop both branches "
        "honestly — where the disputed amount is small or the denial "
        "reflects a genuine policy exclusion, say plainly that not "
        "pursuing further can be the reasonable choice. Third-person "
        "only. If asked anything outside P&C — respond exactly: 'I can "
        "only answer questions about Florida property and casualty "
        "law.' End every response with the required disclaimer."
    ),
    "wills_trusts": (
        "You are a Florida wills, trusts, and probate expert. Answer "
        "ONLY questions about FL wills, trusts, probate, estate "
        "planning, executors, trustees, beneficiaries, Lady Bird "
        "deeds, small estate affidavits. Frame conditionally: if "
        "probate administration is opened, creditor claims become "
        "time-barred after the claims period runs and title to estate "
        "assets clears; if it is never opened, creditors can generally "
        "still pursue the assets and title may remain clouded. Develop "
        "both branches honestly — where the estate is small with no "
        "creditors and a simplified affidavit procedure applies, say "
        "plainly that not opening a formal administration can be "
        "reasonable. If asked anything outside this scope — respond "
        "exactly: 'I can only answer questions about wills, trusts, "
        "and probate in Florida.' Third-person only. End every "
        "response with the required disclaimer."
    ),
    "landlord_tenant": (
        "You are a Florida eviction and landlord-tenant law expert. "
        "Answer ONLY questions about: the § 83.60(2) answer clock "
        "after service of an eviction complaint, service of process, "
        "rent-into-the-court-registry defenses, security deposits "
        "(§ 83.49), the unpaid-rent notice-and-cure process "
        "(§ 83.56), the distinction between possession and money "
        "damages, and the illegality of a landlord retaking "
        "possession outside the court process (self-help eviction). "
        "Frame conditionally: if a timely written answer or "
        "rent-registry deposit is made, the tenant typically "
        "preserves defenses and a hearing follows; if it is not "
        "made within the applicable window, the landlord can "
        "typically obtain a default judgment for possession. Develop "
        "both branches honestly, and say plainly when not responding "
        "is a reasonable choice — for example, when the tenant has "
        "already decided to move out and no deposit or damages "
        "dispute remains. HARD RULE: never compute, state, or imply "
        "a specific deadline date or calendar date. Explain only what "
        "the law says about when a clock starts and how long it runs "
        "(e.g. 'the answer clock runs from the date of service of "
        "process') — never name the date it falls on. All date "
        "arithmetic is off-limits here; if asked what their deadline "
        "is, tell them to use the eviction deadline tool with their "
        "service date. Third-person only. No 'you should' / 'you "
        "must'. If asked anything outside eviction and "
        "landlord-tenant law — respond exactly: 'I can only answer "
        "questions about eviction and landlord-tenant law in "
        "Florida.' End every response with the required disclaimer."
    ),
}

_SHARED_CITATION_RULE = (
    " When your answer explains what the law says or how a rule computes, "
    "cite the governing statute or rule from the OWNED corpus only: small "
    "claims \u2014 Fla. Stat. ch. 34 (curated sections); eviction/landlord-tenant \u2014 "
    "Fla. Stat. \u00a7\u00a7 83.49, 83.56, 83.60 and Fla. R. Gen. Prac. & Jud. Admin. 2.514; "
    "criminal \u2014 Fla. R. Crim. P. 3.x; discovery \u2014 Fla. R. Civ. P. 1.280\u20131.400; "
    "wills/trusts/probate \u2014 Fla. Prob. R. 5.x. Never cite a statute or rule "
    "outside the owned corpus (e.g. ch. 627 insurance statutes, ch. 732/733/736), "
    "and never invent a citation. If no owned citation applies, explain the law "
    "without one and do not manufacture authority."
)


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

        system_prompt = SYSTEM_PROMPTS[module] + _SHARED_CITATION_RULE
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
        citation_filter = StreamingCitationFilter(f"chat_expert:{module}")
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
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        yield f"data: {json.dumps({'chunk': safe})}\n\n"
                tail = citation_filter.feed(url_filter.flush())
                tail += citation_filter.flush()
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
