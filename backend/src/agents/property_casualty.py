"""Module 5 — Property & Casualty Explainer Agent.

Explains Florida property and casualty legal situations.
Handles:
  - first_party_property : homeowner/condo/renter claim under own policy
  - insurance_bad_faith   : § 624.155 civil remedy (UNTOUCHED)
  - premises_liability    : third-party injury on premises (UNTOUCHED)

FIRST_PARTY_PROPERTY contracts:
  - Disclaimer: ALWAYS injected via src.core.upl.apply_disclaimer().
    NEVER inline disclaimer text.
  - Deadlines: LLM extracts date_of_loss as structured data only.
    All date arithmetic routes through backend/deadline/compute.py.
    ZERO date math in this module.
"""

from __future__ import annotations

import base64
import json
import logging
import traceback
from collections.abc import AsyncGenerator
from datetime import date, datetime

from anthropic import AsyncAnthropic

from src.agents.police_report_v2 import compute_risk_score
from src.core.citation_filter import StreamingCitationFilter, filter_citations_text
from src.core.claim_regime import resolve_regime
from src.core.config import settings
from src.core.json_utils import (
    TIGHTENED_PROMPT_SUFFIX,
    parse_llm_json_ladder,
)
from src.core.json_utils import (
    ladder_call_async as _ladder_call,
)
from src.core.upl import apply_disclaimer
from src.core.url_filter import StreamingURLFilter, filter_json_strings
from src.ingestion.pdf_parser import PDFParser
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)

# I-2c — Decision 13 conditional framing: explains the fork the inception
# date determines rather than instructing the user what to do. Surfaced when
# no policy_inception_date is on file for the session (claim_facts
# absent/null) — regime stays "unknown", no regime-specific content is
# selected (I-3 wires the actual rule-set fork).
GUIDANCE_UNKNOWN_POLICY_INCEPTION = (
    "Which statutory deadlines apply depends on when the policy began. If "
    "the policy began on or after 2022-12-16, the SB 2-A deadlines apply — "
    "7 days for the insurer to acknowledge the claim, 60 days to pay or "
    "deny it. If it began before 2022-12-16, the older deadlines applied "
    "instead. The policy inception date is on the declarations page of the "
    "policy; it can also be found in the full policy documents or by "
    "asking the insurance carrier."
)


def _filter_citation_json_strings(obj, agent_name: str):
    """Recursively apply ``filter_citations_text`` to every string in a
    parsed JSON value — mirrors ``agents.explainer``. Applied BEFORE
    ``key_deadlines`` is overwritten with the code-declared computed
    deadlines below, so the deterministic ``governing_rule`` strings the
    engine produces never pass through this filter.
    """
    if isinstance(obj, dict):
        return {k: _filter_citation_json_strings(v, agent_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_filter_citation_json_strings(v, agent_name) for v in obj]
    if isinstance(obj, str):
        return filter_citations_text(obj, agent_name)
    return obj

# ---------------------------------------------------------------------------
# P&C deadline rule keys — I-3a: which clocks run and under which regime is
# now data-declared in deadline/rules.py (`regimes` field) and resolved via
# `pc_rule_keys_for_regime`; this module no longer hardcodes the rule list.
# ---------------------------------------------------------------------------

# Anchored on the estimate-generation date, not date_of_loss — this clock
# cannot be computed until that date is supplied (see _compute_deadlines).
_ESTIMATE_ANCHORED_RULE = "pc_estimate_delivery"
_CRN_ANCHORED_RULE = "pc_crn_cure"           # I-3b — § 624.155(3)(a)
_LOSS_ASSESSMENT_RULE = "pc_loss_assessment" # I-3b — § 627.70132(4)(a) later-of
_PA_CANCEL_RULE = "pc_pa_contract_cancel"    # I-3c — § 626.854(7)
_PA_CANCEL_EMERGENCY_RULE = "pc_pa_contract_cancel_emergency"  # I-3c — § 626.854(7) later-of

# ---------------------------------------------------------------------------
# System prompts — bad_faith + premises_liability are FROZEN
# ---------------------------------------------------------------------------

_FIRST_PARTY_SYSTEM_PROMPT = (
    "You explain Florida first-party residential property insurance "
    "disputes to people with no legal background. "
    "A first-party claim is one the policyholder makes under THEIR OWN "
    "policy against THEIR OWN insurer for property damage "
    "(hurricane, wind, water, roof, fire, theft). "
    "The underlying legal theory is BREACH OF CONTRACT. "
    "Florida's property-insurance claims framework has been reformed "
    "several times in recent years, tightening the reporting and "
    "suit-filing windows and adding a mandatory pre-suit notice step. "
    "When your answer explains what the law says or how a statute "
    "computes, cite the governing statute from the P&C curated set "
    "(ch. 627 claim process, 95.11 limitations, 624.155 bad faith, "
    "626.854 public adjusters, 718.111 condominium allocation). Never "
    "cite outside the owned corpus; never invent a citation. Never "
    "compute a deadline date — explain what the statute provides (e.g. "
    "the 60-day pay-or-deny window) and point to the deadline engine "
    "output. Describe the framework and its deadlines in plain "
    "language, using the computed deadline dates and rule labels "
    "supplied in context below. "
    "IMPORTANT — the claim-reporting deadline and the suit-filing "
    "deadline are TWO SEPARATE CLOCKS, both running from the date of "
    "loss. Satisfying one does NOT satisfy the other. "
    "IMPORTANT — the suit-filing deadline is measured in YEARS, not "
    "months. Do not state or imply a short (e.g. 1-year) suit deadline. "
    "Frame the claim process conditionally: if the claim is reported "
    "within the reporting window, it proceeds under normal review; if "
    "it is reported late, the insurer can raise a late-notice defense "
    "that may reduce or defeat payment. If a denial or lowball offer "
    "is disputed through mediation, appraisal, or a pre-suit notice "
    "followed by litigation, the dispute is preserved and can result "
    "in a higher payment, additional costs, or continued denial "
    "depending on the facts; if it is not disputed before the "
    "suit-filing deadline, the claim becomes permanently time-barred "
    "regardless of its merits. Develop both branches honestly — "
    "where the disputed amount is smaller than the deductible, or "
    "where the denial reflects a genuine policy exclusion, say "
    "plainly that pursuing the claim further may not be worthwhile. "
    "Third-person framing only. Never give legal advice. "
    "Never state what someone should do or must do. "
    "Part of every explanation must cover: what the claim process looks "
    "like, what deadlines apply (using the computed deadlines provided "
    "in the context — do NOT compute or alter them), what documentation "
    "is typically relevant (policy, photos, estimates, correspondence), "
    "and what options exist (mediation, appraisal, notice of intent, "
    "litigation). "
    "Return structured JSON: "
    "{ sub_type_identified: string, "
    "what_this_is: string, "
    "key_deadlines: [{ label, due_date, governing_rule, consequence, "
    "computation_trace: [...] }], "
    "what_usually_happens: string, "
    "typical_timeline: string, "
    "relevant_florida_law: string, "
    "useful_documentation: string[], "
    "watch_out_for: [{ severity: 'high'|'medium'|'low', "
    "description: string, ask_attorney: string }], "
    "resolution_options: string[], "
    "clarifying_questions: string[] | null, "
    "disclaimer: string } "
    "Severity guide for watch_out_for: high = critical "
    "legal risk or statutory deadline; medium = important "
    "consideration or common pitfall; low = helpful tip. "
    "ask_attorney: a plain-English question the user should "
    "raise with their attorney about this warning. "
    "For the key_deadlines array, use the COMPUTED deadlines "
    "provided in the context below — copy them verbatim, including "
    "dates. NEVER compute, derive, or modify a deadline date."
)

# ── FROZEN — bad_faith + premises system prompt, UNTOUCHED ──────────

_BAD_FAITH_PREMISES_SYSTEM_PROMPT = (
    "You explain Florida property and casualty legal "
    "situations to people with no legal background. "
    "For insurance_bad_faith: "
    "Cover what insurance bad faith means under FL Statute "
    "624.155, what the Civil Remedy Notice process is, "
    "what the 60-day cure period means, what typically "
    "happens in FL bad faith cases, what documentation "
    "is typically relevant (denial letters, policy, "
    "correspondence, estimates). "
    "For premises_liability: "
    "Cover what premises liability means in Florida, "
    "the duty of care owed by property owners, what "
    "comparative negligence means in FL, typical timeline "
    "for these cases, what documentation is typically "
    "relevant (incident reports, medical records, "
    "photos, witness info). "
    "For unknown sub_type: explain both and ask "
    "clarifying questions to identify which applies. "
    "Third-person framing only. Never give legal advice. "
    "Never state what someone should do. "
    "Return structured JSON: "
    "{ sub_type_identified: string, "
    "what_this_is: string, "
    "what_usually_happens: string, "
    "typical_timeline: string, "
    "relevant_florida_law: string, "
    "useful_documentation: string[], "
    "watch_out_for: [{ severity: 'high'|'medium'|'low', "
    "description: string, ask_attorney: string }], "
    "typical_outcomes: string[], "
    "clarifying_questions: string[] | null, "
    "disclaimer: string } "
    "Severity guide for watch_out_for: high = critical "
    "legal risk or statutory deadline; medium = important "
    "consideration or common pitfall; low = helpful tip. "
    "ask_attorney: a plain-English question the user should "
    "raise with their attorney about this warning."
)

# Custom __str__ for frozen prompt so it fits into existing code paths
class _FrozenSystemPrompt(str):
    pass

SYSTEM_PROMPT = _FrozenSystemPrompt(_BAD_FAITH_PREMISES_SYSTEM_PROMPT)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class PropertyCasualtyExplainer:
    """Streaming property & casualty explainer with optional document support."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self._pdf_parser = PDFParser()
        self._db = DatabaseManager()

    def _resolve_claim_regime(self, session_id: str) -> dict:
        """I-2c — resolve pre/post/unknown from the user-supplied policy
        inception date on file for this session (Option A ruling
        2026-08-20: claim_facts is keyed by session_id, never by entities
        passed in on the request). The explain flow always has a session
        by the time this is called (existing session or one just created),
        so this always returns a dict — "not applicable" no longer exists.

        provenance is always 'user_supplied' — see claim_facts.
        """
        fact = self._db.get_claim_fact(session_id)
        inception = fact.get("policy_inception_date") if fact else None
        inception_date = date.fromisoformat(inception) if inception else None
        regime = resolve_regime(inception_date)
        if regime == "unknown":
            return {"regime": "unknown", "guidance": GUIDANCE_UNKNOWN_POLICY_INCEPTION}
        return {"regime": regime}

    # ── content builders ────────────────────────────────────────────────

    @staticmethod
    def _guess_media_type(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif", "webp": "image/webp",
        }.get(ext, "image/jpeg")

    @staticmethod
    def _is_image(filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}

    @staticmethod
    def _is_pdf(filename: str) -> bool:
        return filename.rsplit(".", 1)[-1].lower() == "pdf" if "." in filename else False

    @staticmethod
    def _parse_date_of_loss(entities: dict) -> date | None:
        """Extract date_of_loss from entities dict. Returns None if absent/unparseable.

        This is the ONLY date extraction in this module — it reads what was
        already parsed upstream. No computation, no derivation.
        """
        raw = entities.get("date_of_loss") or entities.get("date_of_loss_str")
        return PropertyCasualtyExplainer._parse_date(raw)

    @staticmethod
    def _parse_estimate_generated_date(entities: dict) -> date | None:
        """Extract estimate_generated_date from entities dict (I-3a). Returns
        None if absent/unparseable — the § 627.70131(3)(e) estimate-delivery
        clock runs from the date the insurer's adjuster generates the
        estimate, not from date_of_loss, and that date is not otherwise
        available anywhere in the current data flow. The caller (a future
        API consumer or UI) supplies it the same free-form way as
        date_of_loss; until supplied, pc_estimate_delivery is not computed
        rather than guessed from an unrelated anchor.
        """
        raw = entities.get("estimate_generated_date") or entities.get("estimate_generated_date_str")
        return PropertyCasualtyExplainer._parse_date(raw)

    @staticmethod
    def _parse_date(raw) -> date | None:
        if not raw or not isinstance(raw, str):
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()  # noqa: DTZ007
            except ValueError:
                continue
        return None

    def _compute_deadlines(
        self,
        loss_date: date,
        regime: str | None = None,
        estimate_generated_date: date | None = None,
        crn_filed_date: date | None = None,          # I-3b — pc_crn_cure
        association_vote_date: date | None = None,   # I-3b — pc_loss_assessment
        pa_contract_executed_date: date | None = None,   # I-3c — PA cancellation
    ) -> list[dict]:
        """Compute all P&C statutory deadlines from a date of loss.

        Routes through the deterministic deadline engine — ZERO date math here.
        `regime` selects which declared P&C clocks apply (I-3a) — None
        computes every declared clock (pre-I-3a behavior when no regime has
        been resolved for this session); "unknown" computes none.
        `pc_estimate_delivery` is anchored on `estimate_generated_date`, not
        `loss_date` — it is skipped (never computed from date_of_loss) when
        that date has not been supplied. Likewise `pc_crn_cure` needs
        `crn_filed_date`, `pc_loss_assessment` needs `association_vote_date`
        (I-3b), and the PA cancellation clocks need
        `pa_contract_executed_date` (I-3c) — missing anchors skip and
        escalate, never substitute.
        """
        from deadline.compute import compute_deadline_for_event
        from deadline.rules import RULES, pc_rule_keys_for_regime

        closure_dates: frozenset[date] = frozenset()
        results: list[dict] = []

        for rule_key in pc_rule_keys_for_regime(regime):
            extra_dates: dict[str, date] = {}
            if rule_key == _ESTIMATE_ANCHORED_RULE:
                if estimate_generated_date is None:
                    continue
                anchor_date = estimate_generated_date
            elif rule_key == _CRN_ANCHORED_RULE:
                if crn_filed_date is None:
                    continue
                anchor_date = crn_filed_date
            elif rule_key == _LOSS_ASSESSMENT_RULE:
                if association_vote_date is None:
                    continue
                anchor_date = loss_date
                extra_dates = {"association_vote": association_vote_date}
            elif rule_key == _PA_CANCEL_RULE:
                if pa_contract_executed_date is None:
                    continue
                anchor_date = pa_contract_executed_date
            elif rule_key == _PA_CANCEL_EMERGENCY_RULE:
                if pa_contract_executed_date is None:
                    continue
                anchor_date = loss_date
                extra_dates = {"pa_contract_executed": pa_contract_executed_date}
            else:
                anchor_date = loss_date
            try:
                result = compute_deadline_for_event(
                    rule_key=rule_key,
                    event_date=anchor_date,
                    service_method="personal",  # statutory, not court-service
                    circuit=None,
                    closure_dates=closure_dates,
                    has_local_closure_data=True,
                    today=date.today(),  # noqa: DTZ011
                    extra_dates=extra_dates or None,
                )
                for dl in result.deadlines:
                    results.append({
                        "label": dl.label,
                        "due_date": dl.due_date.isoformat(),
                        "governing_rule": dl.governing_rule,
                        "severity": dl.severity,
                        "consequence": dl.consequence,
                        "is_past": dl.is_past,
                        "deadline_type": RULES[rule_key].get("deadline_type", "court_filing"),
                        "computation_trace": dl.computation_trace,
                    })
            except Exception:
                logger.warning("Deadline computation failed for rule %s: %s",
                               rule_key, traceback.format_exc())
        return results

    def _build_entities_text(self, entities: dict) -> str:
        """Format entities dict as readable context lines."""
        if not entities:
            return "No specific situation details provided."
        lines = ["Situation details:"]
        for k, v in entities.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def _build_deadline_context(self, deadlines: list[dict]) -> str:
        """Format computed deadlines as LLM context — verbatim, no alteration."""
        if not deadlines:
            return ""
        lines = ["\nComputed deadlines (DO NOT MODIFY — use verbatim):"]
        for dl in deadlines:
            lines.append(
                f"  - {dl['label']}: {dl['due_date']} "
                f"({dl['governing_rule']}, severity={dl['severity']}, "
                f"is_past={dl['is_past']})"
            )
        return "\n".join(lines)

    # ── system prompt selection ───────────────────────────────────────

    def _select_system_prompt(self, sub_type: str) -> str:
        if sub_type == "first_party_property":
            return _FIRST_PARTY_SYSTEM_PROMPT
        return _BAD_FAITH_PREMISES_SYSTEM_PROMPT

    # ── user text builder ──────────────────────────────────────────────

    def _build_user_text(
        self,
        sub_type: str,
        entities: dict,
        lang_label: str,
        doc_text: str | None = None,
        deadlines: list[dict] | None = None,
        claim_regime: dict | None = None,
    ) -> str:
        """Assemble the main user prompt text."""
        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")
        parts.append(f"Sub-type: {sub_type}.")
        parts.append(self._build_entities_text(entities))

        if claim_regime and claim_regime.get("regime") == "unknown":
            # I-2c live-gate finding: with the policy inception date unknown,
            # the model must NOT produce deadline framework content — which
            # regime's clocks apply is exactly the unknown. Escalate instead.
            parts.append(
                "IMPORTANT: the policy inception date is unknown. Do NOT "
                "include a key_deadlines field and do NOT present any "
                "deadline labels or windows. Instead explain only that the "
                "applicable deadlines depend on when the policy began, and "
                "direct the user to the declarations page of the policy for "
                "that date."
            )
        elif deadlines:
            parts.append(self._build_deadline_context(deadlines))

        if doc_text:
            parts.append(
                f"\nSupporting document text (up to 24,000 chars):\n"
                f"{doc_text[:24000]}"
            )

        parts.append(
            "Explain this Florida property/casualty situation. "
            "Return ONLY a valid JSON object. No markdown. No preamble."
        )
        return "\n".join(parts)

    # ── streaming ───────────────────────────────────────────────────────

    async def explain_stream(
        self,
        sub_type: str,
        entities: dict,
        language: str = "en",
        file_bytes: bytes | None = None,
        filename: str | None = None,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a property/casualty explanation as SSE chunks."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: str | None = None
        is_first_party = sub_type == "first_party_property"

        # ── I-2c: resolve claim regime from the user-supplied policy
        # inception date, keyed by session_id (Option A ruling 2026-08-20).
        # {"regime": "unknown", ...} means checked-and-absent — escalate.
        claim_regime = self._resolve_claim_regime(session_id) if session_id else None

        # ── first-party: compute deadlines from date_of_loss ─────────
        computed_deadlines: list[dict] | None = None
        if is_first_party and not (claim_regime and claim_regime["regime"] == "unknown"):
            loss_date = self._parse_date_of_loss(entities)
            if loss_date:
                computed_deadlines = self._compute_deadlines(
                    loss_date,
                    regime=claim_regime.get("regime") if claim_regime else None,
                    estimate_generated_date=self._parse_estimate_generated_date(entities),
                )

        # ── optional file ────────────────────────────────────────────
        if file_bytes and filename:
            if self._is_image(filename):
                media_type = self._guess_media_type(filename)
                b64 = base64.b64encode(file_bytes).decode("ascii")
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                })
            elif self._is_pdf(filename):
                try:
                    extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
                except Exception:
                    logger.error("PDF extraction failed:\n%s", traceback.format_exc())
                    yield f"data: {json.dumps(apply_disclaimer({'error': True, 'message': 'Could not extract text from PDF.'}, lang=language))}\n\n"
                    return
                doc_text = extraction.get("raw_text", "")
                if not doc_text.strip():
                    yield f"data: {json.dumps(apply_disclaimer({'error': True, 'message': 'No readable text found.'}, lang=language))}\n\n"
                    return
            else:
                yield f"data: {json.dumps(apply_disclaimer({'error': True, 'message': 'Unsupported file type.'}, lang=language))}\n\n"
                return

        # ── text portion ──────────────────────────────────────────────
        system_prompt = self._select_system_prompt(sub_type)
        user_text = self._build_user_text(sub_type, entities, lang_label, doc_text, computed_deadlines, claim_regime)
        user_content.append({"type": "text", "text": user_text})

        # ── leading metadata chunk ────────────────────────────────────
        # session_id and claim_regime are DETERMINISTIC values the client
        # needs for /facts and regime display. They must not ride inside the
        # model's JSON — a token-capped/truncated answer would silently drop
        # them (I-2c live-gate finding 2026-08-20). Emitted up front,
        # independent of the model stream.
        if session_id:
            meta: dict = {"type": "session", "session_id": session_id}
            if claim_regime:
                meta["claim_regime"] = claim_regime
            yield f"data: {json.dumps(meta)}\n\n"

        try:
            full_text = ""
            url_filter = StreamingURLFilter("property_casualty")
            citation_filter = StreamingCitationFilter("property_casualty")
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        yield f"data: {safe}\n\n"
            tail = citation_filter.feed(url_filter.flush())
            tail += citation_filter.flush()
            if tail:
                yield f"data: {tail}\n\n"

            # ── Post-stream: inject computed deadlines if LLM dropped them ──
            async def _retry_pc() -> str:
                # Decision 20: one tightened re-call to recover the JSON.
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": list(user_content) + [{"type": "text", "text": TIGHTENED_PROMPT_SUFFIX.strip()}]}],
                )
                return response.content[0].text

            parsed, degraded = await parse_llm_json_ladder(
                full_text, site="property_casualty", expect="dict",
                retry_call=_retry_pc,
            )
            if degraded:
                parsed = None
            else:
                try:
                    parsed = filter_json_strings(parsed, "property_casualty")
                    parsed = _filter_citation_json_strings(parsed, "property_casualty")
                    if is_first_party and computed_deadlines:
                        parsed["key_deadlines"] = computed_deadlines
                    if claim_regime and claim_regime.get("regime") == "unknown":
                        # Deterministic boundary: regime unknown means no
                        # deadline content survives, whatever the model emitted.
                        parsed.pop("key_deadlines", None)
                    if claim_regime:
                        parsed["claim_regime"] = claim_regime
                    if session_id:
                        parsed["session_id"] = session_id
                    # ── Compute risk score from watch_out_for ──
                    all_findings = [
                        {"severity": w.get("severity", "low"), "description": w.get("description", w if isinstance(w, str) else "")}
                        for w in parsed.get("watch_out_for", [])
                    ]
                    if all_findings:
                        risk = compute_risk_score(all_findings)
                        risk["type"] = "risk_analysis"
                        yield f"data: {json.dumps(risk)}\n\n"
                    # ── Re-emit full payload with disclaimer ──
                    final = apply_disclaimer(parsed, lang=language)
                    yield f"data: {json.dumps(final)}\n\n"
                except (KeyError, TypeError):
                    # Enrichment-only failure after a valid parse: the raw
                    # stream has already been delivered — log and skip.
                    logger.error(
                        "PropertyCasualty post-parse enrichment failed:\n%s",
                        traceback.format_exc(),
                    )

        except Exception:
            logger.error("PropertyCasualtyExplainer stream error:\n%s", traceback.format_exc())
            yield f"data: {json.dumps(apply_disclaimer({'error': True, 'message': 'Explanation could not be generated.'}, lang=language))}\n\n"

    # ── non-streaming ───────────────────────────────────────────────────

    async def explain(
        self,
        sub_type: str,
        entities: dict,
        language: str = "en",
        file_bytes: bytes | None = None,
        filename: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """Non-streaming explanation."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: str | None = None
        is_first_party = sub_type == "first_party_property"

        # ── I-2c: resolve claim regime (see explain_stream for contract) ──
        claim_regime = self._resolve_claim_regime(session_id) if session_id else None

        # ── first-party: compute deadlines ──────────────────────────
        computed_deadlines: list[dict] | None = None
        if is_first_party and not (claim_regime and claim_regime["regime"] == "unknown"):
            loss_date = self._parse_date_of_loss(entities)
            if loss_date:
                computed_deadlines = self._compute_deadlines(
                    loss_date,
                    regime=claim_regime.get("regime") if claim_regime else None,
                    estimate_generated_date=self._parse_estimate_generated_date(entities),
                )

        if file_bytes and filename:
            if self._is_image(filename):
                b64 = base64.b64encode(file_bytes).decode("ascii")
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": self._guess_media_type(filename), "data": b64},
                })
            elif self._is_pdf(filename):
                try:
                    extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
                except Exception:
                    logger.error("PDF extraction failed in explain:\n%s", traceback.format_exc())
                    return apply_disclaimer({"error": True, "message": "Could not extract text."}, lang=language)
                doc_text = extraction.get("raw_text", "")

        system_prompt = self._select_system_prompt(sub_type)
        user_text = self._build_user_text(sub_type, entities, lang_label, doc_text, computed_deadlines, claim_regime)
        user_content.append({"type": "text", "text": user_text})

        async def _call(prompt: str) -> str:
            msg_content = user_content
            if prompt:  # retry pass: append the tightened instruction
                msg_content = list(user_content) + [{"type": "text", "text": prompt}]
            response = await self.client.messages.create(
                model=self.model, max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": msg_content}],
            )
            return response.content[0].text

        try:
            parsed, degraded = await _ladder_call(
                _call, "", site="property_casualty_explain", expect="dict"
            )
            if degraded:
                return apply_disclaimer({"error": True, "message": "Explanation could not be generated."}, lang=language)
            parsed = _filter_citation_json_strings(parsed, "property_casualty")

            # ── Inject computed deadlines ──
            if is_first_party and computed_deadlines:
                parsed["key_deadlines"] = computed_deadlines
            if claim_regime and claim_regime.get("regime") == "unknown":
                parsed.pop("key_deadlines", None)
            if claim_regime:
                parsed["claim_regime"] = claim_regime
            if session_id:
                parsed["session_id"] = session_id

            # ── Compute deterministic risk score ──
            all_findings = [
                {"severity": w.get("severity", "low"), "description": w.get("description", w if isinstance(w, str) else "")}
                for w in parsed.get("watch_out_for", [])
            ]
            if all_findings:
                parsed["risk_analysis"] = compute_risk_score(all_findings)

            # ── Apply shared disclaimer via middleware ──
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("PropertyCasualtyExplainer error:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": "Explanation could not be generated."}, lang=language)
