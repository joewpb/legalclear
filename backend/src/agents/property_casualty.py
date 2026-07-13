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
from datetime import date, datetime
from typing import AsyncGenerator

from anthropic import AsyncAnthropic

from src.agents.police_report_v2 import compute_risk_score
from src.core.config import settings
from src.core.upl import apply_disclaimer
from src.ingestion.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# P&C deadline rule keys — consumed by the deterministic engine
# ---------------------------------------------------------------------------

_PC_DEADLINE_RULES = [
    "pc_report_claim",
    "pc_supplemental_claim",
    "pc_file_suit",
    "pc_pay_or_deny",
    "pc_notice_of_intent",
]

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
    "The statutory framework is Chapter 627, Part X (sections "
    "627.701–627.7155), reformed by SB 2-D (May 2022), "
    "SB 2-A (Dec 2022), and HB 837 (Mar 2023). "
    "Key statutes the user needs to know: "
    "§ 627.70132 — 1 year to report the claim, 18 months for supplemental; "
    "§ 95.11(2)(e) — 5 YEARS to file suit, both from date of loss; "
    "§ 627.70131 — insurer must pay or deny within 60 days; "
    "§ 627.70152 — pre-suit Notice of Intent is a mandatory gate; "
    "§ 627.7015 — DFS mediation (free, non-binding); "
    "§ 627.7152 — post-loss AOB is prohibited. "
    "IMPORTANT — the 5-year suit deadline and 1-year report deadline are "
    "TWO SEPARATE CLOCKS. Both run from the date of loss. Satisfying one "
    "does NOT satisfy the other. "
    "IMPORTANT — the statute of limitations to sue is 5 YEARS under "
    "§ 95.11(2)(e), NOT 1 year. Do not state or imply a 1-year suit deadline. "
    "Third-person framing only. Never give legal advice. "
    "Never state what someone should do or must do. "
    "Part of every explanation must cover: what the claim process looks "
    "like, what deadlines apply (using the computed deadlines provided "
    "in the context — do NOT compute or alter them), what documentation "
    "is typically relevant (policy, photos, estimates, correspondence), "
    "and what options exist (mediation, appraisal, NOI, litigation). "
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
    def _strip_fences(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return text

    @staticmethod
    def _parse_date_of_loss(entities: dict) -> date | None:
        """Extract date_of_loss from entities dict. Returns None if absent/unparseable.

        This is the ONLY date extraction in this module — it reads what was
        already parsed upstream. No computation, no derivation.
        """
        raw = entities.get("date_of_loss") or entities.get("date_of_loss_str")
        if not raw or not isinstance(raw, str):
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _compute_deadlines(self, loss_date: date) -> list[dict]:
        """Compute all P&C statutory deadlines from a date of loss.

        Routes through the deterministic deadline engine — ZERO date math here.
        """
        from deadline.compute import compute_deadline_for_event
        from deadline.rules import RULES

        closure_dates: frozenset[date] = frozenset()
        results: list[dict] = []

        for rule_key in _PC_DEADLINE_RULES:
            try:
                result = compute_deadline_for_event(
                    rule_key=rule_key,
                    event_date=loss_date,
                    service_method="personal",  # statutory, not court-service
                    circuit=None,
                    closure_dates=closure_dates,
                    has_local_closure_data=True,
                    today=date.today(),
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
    ) -> str:
        """Assemble the main user prompt text."""
        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")
        parts.append(f"Sub-type: {sub_type}.")
        parts.append(self._build_entities_text(entities))

        if deadlines:
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
    ) -> AsyncGenerator[str, None]:
        """Stream a property/casualty explanation as SSE chunks."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: str | None = None
        is_first_party = sub_type == "first_party_property"

        # ── first-party: compute deadlines from date_of_loss ─────────
        computed_deadlines: list[dict] | None = None
        if is_first_party:
            loss_date = self._parse_date_of_loss(entities)
            if loss_date:
                computed_deadlines = self._compute_deadlines(loss_date)

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
        user_text = self._build_user_text(sub_type, entities, lang_label, doc_text, computed_deadlines)
        user_content.append({"type": "text", "text": user_text})

        try:
            full_text = ""
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    yield f"data: {chunk}\n\n"

            # ── Post-stream: inject computed deadlines if LLM dropped them ──
            try:
                parsed = json.loads(self._strip_fences(full_text))
                if is_first_party and computed_deadlines:
                    parsed["key_deadlines"] = computed_deadlines
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
            except (json.JSONDecodeError, KeyError):
                pass

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
    ) -> dict:
        """Non-streaming explanation."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: str | None = None
        is_first_party = sub_type == "first_party_property"

        # ── first-party: compute deadlines ──────────────────────────
        computed_deadlines: list[dict] | None = None
        if is_first_party:
            loss_date = self._parse_date_of_loss(entities)
            if loss_date:
                computed_deadlines = self._compute_deadlines(loss_date)

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
        user_text = self._build_user_text(sub_type, entities, lang_label, doc_text, computed_deadlines)
        user_content.append({"type": "text", "text": user_text})

        try:
            response = await self.client.messages.create(
                model=self.model, max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            )
            parsed = json.loads(self._strip_fences(response.content[0].text))

            # ── Inject computed deadlines ──
            if is_first_party and computed_deadlines:
                parsed["key_deadlines"] = computed_deadlines

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
