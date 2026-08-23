"""I-8 — LLM-on-tap actions (Phase I finale, 2026-08-23).

Spec §7: the model is allowed ONLY on explicit user action, and never in
date arithmetic, coverage decisions, settlement prediction, or on-the-fly
phase content. Five taps:

  explain_letter   — user uploads a letter they received; the model
                     summarizes it in plain language and flags which
                     deadline-related statements it contains (verbatim —
                     never computed, never interpreted as dates).
  describe_item    — user's notes about one item -> a single inventory row.
  notes_to_demand  — user's notes -> a draft demand letter body.
  define_term      — a term -> plain-language definition; citations only
                     from the P&C curated set (filter-enforced).
  classify_document— an uploaded document -> a known P&C document type.

Hard rules baked into every prompt:
  - Never compute, derive, or alter any deadline date.
  - Never decide whether a peril is covered.
  - Never predict a settlement value.
  - Third-person framing; no legal advice.
  - Cite only from the P&C curated set (deterministic citation filter runs
    on every output string regardless of the prompt).

Provider failures return a clean, user-facing error payload — the caller
never gets a stack trace or a raw provider error.
"""

from __future__ import annotations

import base64
import json
import logging
import traceback

from anthropic import AsyncAnthropic

from src.core.citation_filter import filter_citations_text
from src.core.config import settings
from src.core.json_utils import strip_markdown_fences
from src.core.upl import apply_disclaimer
from src.core.url_filter import filter_json_strings
from src.ingestion.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_PROVIDER_ERROR_MESSAGE = (
    "This action needs the explanation service, which is temporarily "
    "unavailable. Please try again later."
)

_COMMON_RULES = (
    "You are part of a Florida legal-information product for people with no "
    "legal background. Hard rules: NEVER compute, derive, or alter any "
    "deadline date. NEVER decide whether a peril is covered. NEVER predict "
    "a settlement value. NEVER give legal advice or tell the user what to "
    "do. Use third-person framing and plain language. Cite Florida law "
    "ONLY from the P&C curated set you are given; never invent a citation. "
)

_CURATED_LIST = (
    "Fla. Stat. § 627.70131, Fla. Stat. § 627.70132, Fla. Stat. § 627.7011, "
    "Fla. Stat. § 627.702, Fla. Stat. § 627.7015, Fla. Stat. § 627.70152, "
    "Fla. Stat. § 627.7152, Fla. Stat. § 627.7142, Fla. Stat. § 627.706, "
    "Fla. Stat. § 627.7074, Fla. Stat. § 95.11, Fla. Stat. § 624.155, "
    "Fla. Stat. § 626.854, Fla. Stat. § 718.111"
)

_SYSTEM_EXPLAIN_LETTER = (
    _COMMON_RULES
    + f"P&C curated citation set: {_CURATED_LIST}. "
    + "The user uploads a letter they received about an insurance claim. "
    + "Summarize what the letter says, in plain language, section by "
    + "section if it has sections. For any statement in the letter that "
    + "mentions a deadline or a time window, quote it VERBATIM and say "
    + "only 'the letter states this window' — do not compute dates, do not "
    + "say whether the window is met, do not interpret it against any "
    + "calendar. List the letter's requests of the reader (documents, "
    + "statements, meetings) neutrally. Return ONLY JSON: "
    + "{summary: string, deadline_statements: [{quote: string, note: "
    + "string}], requests_of_reader: string[], type_guess: string, "
    + "citations: string[]}"
)

_SYSTEM_DESCRIBE_ITEM = (
    _COMMON_RULES
    + "The user describes one household item for a fire contents inventory. "
    + "Return ONLY JSON with exactly these keys: "
    + "{room, item, brand, model, serial, qty, age_years, price_paid, "
    + "condition, cost_new_today, price_source}. Fill each field from the "
    + "user's description; use empty string when unknown — NEVER invent a "
    + "value. qty is a number. age_years is a number or empty string. "
    + "condition is one of: new, good, fair, poor. The note about fraud "
    + "is handled by deterministic code; do not lecture."
)

_SYSTEM_NOTES_TO_DEMAND = (
    _COMMON_RULES
    + f"P&C curated citation set: {_CURATED_LIST}. "
    + "The user provides notes about an insurance claim dispute. Draft the "
    + "BODY of a written demand letter from the policyholder to the "
    + "insurer: state the claim number, describe the disagreement in the "
    + "policyholder's own framing, and request a written response. Plain, "
    + "factual, no threats, no legal conclusions, no dates computed. "
    + "Return ONLY JSON: {body: string, citations: string[]}"
)

_SYSTEM_DEFINE_TERM = (
    _COMMON_RULES
    + f"P&C curated citation set: {_CURATED_LIST}. "
    + "The user asks what a term means in the context of a Florida "
    + "property insurance claim. Define it in plain language. If (and only "
    + "if) the term's meaning comes from a statute in the curated set, "
    + "include that citation; otherwise return an empty citations array. "
    + "Return ONLY JSON: {term: string, definition: string, citations: "
    + "string[], plain_language_note: string}"
)

_SYSTEM_CLASSIFY_DOCUMENT = (
    _COMMON_RULES
    + "The user uploads a document from an insurance claim. Classify it "
    + "into exactly one of: reservation_of_rights_letter, denial_letter, "
    + "estimate, settlement_check, examination_under_oath_demand, "
    + "policy_document, court_filing, correspondence, other. Return ONLY "
    + "JSON: {document_type: string, confidence: 'high'|'medium'|'low', "
    + "one_line_summary: string, citations: string[]}"
)

# Document-type taxonomy for the classifier tap (deterministic label set).
DOCUMENT_TYPES = (
    "reservation_of_rights_letter", "denial_letter", "estimate",
    "settlement_check", "examination_under_oath_demand", "policy_document",
    "court_filing", "correspondence", "other",
)


def _is_image(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}


def _is_pdf(filename: str) -> bool:
    return filename.rsplit(".", 1)[-1].lower() == "pdf" if "." in filename else False


def _guess_media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "gif": "image/gif", "webp": "image/webp",
    }.get(ext, "image/jpeg")


def _filter_citation_json_strings(obj, agent_name: str):
    """Recursively apply ``filter_citations_text`` to every string in a
    parsed JSON value — including strings nested inside lists and dicts
    (mirrors agents.property_casualty). A fabricated citation inside a
    list field (e.g. the ``citations`` array) is stripped the same as one
    in a top-level string field."""
    if isinstance(obj, dict):
        return {k: _filter_citation_json_strings(v, agent_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_filter_citation_json_strings(v, agent_name) for v in obj]
    if isinstance(obj, str):
        return filter_citations_text(obj, agent_name)
    return obj


def _sanitize_parsed(parsed: dict, agent_name: str = "pc_llm_tap") -> dict:
    """URL-filter + citation-filter every string in a parsed JSON payload."""
    return _filter_citation_json_strings(
        filter_json_strings(parsed, agent_name), agent_name,
    )


class PcLlmTap:
    """Explicit-user-action LLM taps for the P&C module."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = _MODEL
        self._pdf_parser = PDFParser()

    async def _call(self, system: str, user_text: str, user_image_b64: dict | None = None) -> dict:
        content: list[dict] = []
        if user_image_b64 is not None:
            content.append(user_image_b64)
        content.append({"type": "text", "text": user_text})
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[{"type": "text", "text": system}],
            messages=[{"role": "user", "content": content}],
        )
        raw = response.content[0].text
        parsed = json.loads(strip_markdown_fences(raw))
        return _sanitize_parsed(parsed)

    async def _file_to_content(self, file_bytes: bytes, filename: str) -> tuple[dict | str | None, str | None]:
        """Return (user_content_entry_or_none, error_or_none)."""
        if _is_image(filename):
            b64 = base64.b64encode(file_bytes).decode("ascii")
            return {"type": "image", "source": {
                "type": "base64", "media_type": _guess_media_type(filename), "data": b64,
            }}, None
        if _is_pdf(filename):
            try:
                extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
            except Exception:
                logger.error("tap PDF extraction failed:\n%s", traceback.format_exc())
                return None, "Could not extract text from that file."
            text = extraction.get("raw_text", "")
            if not text.strip():
                return None, "No readable text found in that file."
            return f"Document text (up to 24000 chars):\n{text[:24000]}", None
        return None, "Unsupported file type."

    # ── taps ────────────────────────────────────────────────────────────

    async def explain_letter(self, file_bytes: bytes, filename: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        entry, err = await self._file_to_content(file_bytes, filename)
        if err:
            return apply_disclaimer({"error": True, "message": err}, lang=language)
        if isinstance(entry, dict):
            content = [entry, {"type": "text", "text": f"Explain this letter. Respond entirely in {lang_label}. Return ONLY JSON."}]
        else:
            content = [{"type": "text", "text": f"{entry}\n\nExplain this letter. Respond entirely in {lang_label}. Return ONLY JSON."}]
        try:
            response = await self.client.messages.create(
                model=self.model, max_tokens=2048,
                system=[{"type": "text", "text": _SYSTEM_EXPLAIN_LETTER}],
                messages=[{"role": "user", "content": content}],
            )
            parsed = json.loads(strip_markdown_fences(response.content[0].text))
            parsed = _sanitize_parsed(parsed)
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("explain_letter tap failed:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": _PROVIDER_ERROR_MESSAGE}, lang=language)

    async def describe_item(self, notes: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        try:
            parsed = await self._call(
                _SYSTEM_DESCRIBE_ITEM,
                f"Item description: {notes[:4000]}\nRespond entirely in {lang_label}. Return ONLY JSON.",
            )
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("describe_item tap failed:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": _PROVIDER_ERROR_MESSAGE}, lang=language)

    async def notes_to_demand(self, notes: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        try:
            parsed = await self._call(
                _SYSTEM_NOTES_TO_DEMAND,
                f"Policyholder's notes about the dispute: {notes[:8000]}\n"
                f"Respond entirely in {lang_label}. Return ONLY JSON.",
            )
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("notes_to_demand tap failed:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": _PROVIDER_ERROR_MESSAGE}, lang=language)

    async def define_term(self, term: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        try:
            parsed = await self._call(
                _SYSTEM_DEFINE_TERM,
                f"Term to define: {term[:200]}\nRespond entirely in {lang_label}. Return ONLY JSON.",
            )
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("define_term tap failed:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": _PROVIDER_ERROR_MESSAGE}, lang=language)

    async def classify_document(self, file_bytes: bytes, filename: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        entry, err = await self._file_to_content(file_bytes, filename)
        if err:
            return apply_disclaimer({"error": True, "message": err}, lang=language)
        if isinstance(entry, dict):
            content = [entry, {"type": "text", "text": f"Classify this document. Respond entirely in {lang_label}. Return ONLY JSON."}]
        else:
            content = [{"type": "text", "text": f"{entry}\n\nClassify this document. Respond entirely in {lang_label}. Return ONLY JSON."}]
        try:
            response = await self.client.messages.create(
                model=self.model, max_tokens=1024,
                system=[{"type": "text", "text": _SYSTEM_CLASSIFY_DOCUMENT}],
                messages=[{"role": "user", "content": content}],
            )
            parsed = json.loads(strip_markdown_fences(response.content[0].text))
            if parsed.get("document_type") not in DOCUMENT_TYPES:
                parsed["document_type"] = "other"
            parsed = _sanitize_parsed(parsed)
            return apply_disclaimer(parsed, lang=language)
        except Exception:
            logger.error("classify_document tap failed:\n%s", traceback.format_exc())
            return apply_disclaimer({"error": True, "message": _PROVIDER_ERROR_MESSAGE}, lang=language)
