"""LLM trigger-event extractor — Phase 4, Stage 1.

THE LLM MUST NEVER COMPUTE OR OUTPUT A DEADLINE DATE.
It extracts only what is explicitly stated in the document text.

Schema contract: one call per document → list of trigger events.
Retry once on schema-invalid output; escalate on second failure.
"""

from __future__ import annotations

import calendar
import json
import logging
import re
from datetime import date
from typing import Any

import anthropic

from .rules import KNOWN_DOCUMENT_TYPES

logger = logging.getLogger(__name__)

# Date-kind labels the extractor may emit. Deadline rules declare which of
# these they can consume (rules.py required_anchors); anything off-schema is
# coerced to "unknown" so it can never satisfy a rule's anchor downstream.
ALLOWED_EVENT_TYPES: frozenset[str] = frozenset(
    {"served", "filed", "issued", "rendered", "hearing", "unknown"}
)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


SYSTEM_PROMPT = """\
You are a legal document trigger-event extractor. Your ONLY job is to identify \
facts that are explicitly stated in the document: dates, service methods, \
document type, case metadata. You do NOT compute deadlines or infer information \
not in the text.

Return valid JSON matching this schema exactly — no markdown fences, no extra keys:
{
  "events": [
    {
      "event_type": "served" | "filed" | "issued" | "rendered" | "hearing" | "unknown",
      "event_date": "YYYY-MM-DD" | null,
      "service_method": "personal" | "mail" | "e_service" | "publication" | "unknown",
      "document_type": "<one of the allowed types below>" | "unknown",
      "circuit": <integer> | null,
      "county": "<string>" | null,
      "case_number": "<string>" | null,
      "raw_text_excerpt": "<verbatim sentence from the document that states the date/service>",
      "confidence": <0.0 to 1.0>
    }
  ],
  "escalation_needed": true | false,
  "escalation_reason": "<string>" | null
}

Allowed document_type values:
civil_summons, eviction_complaint, foreclosure_complaint, family_law_petition,
small_claims_summons, notice_of_appeal, motion_for_rehearing, discovery_request, unknown

Rules you must follow:
1. If a date is not explicitly stated in the document, set event_date to null.
2. If the service method is not explicitly stated, set it to "unknown".
3. If the document type cannot be determined with confidence, set it to "unknown".
4. Never compute, infer, or derive a date from surrounding context.
5. If you cannot identify any trigger event, return an empty events array and
   set escalation_needed to true.
6. "unknown" is always a valid output. A confident wrong answer is worse than
   admitting uncertainty.
7. Label each date by what it IS, not by what a deadline needs. "served" means
   the document explicitly states the date of SERVICE of process on the
   recipient. A clerk/judge signature or issuance date (e.g. "DATED this 14th
   day of August, 2026") is "issued", NEVER "served". A signed order/judgment
   filing date is "rendered". A scheduled court appearance is "hearing". If
   the date's role is unclear, use "unknown".
8. NEVER invent or guess a date. Do NOT output placeholder dates such as
   2025-01-01, 1970-01-01, or any January 1 / round-number date. Every
   non-null event_date MUST be a date that appears verbatim in the document
   text — if no date is stated, set event_date to null. The raw_text_excerpt
   must contain that exact date. A returned date that cannot be found in the
   document is treated as a hallucination and will be discarded.
"""


def _date_variant_families(iso_date_str: str) -> dict[str, set[str]]:
    """Build the accepted textual representations of an ISO date, grouped by
    the variant family that produced them (iso/numeric-us/textual/ordinal).

    Shared by `_date_appears_in_text` (matching) and the rejection logger in
    `_sanitize_events` (diagnostics) so the two never drift out of sync.
    """
    d = date.fromisoformat(iso_date_str)

    yr = str(d.year)
    mm, dd = f"{d.month:02d}", f"{d.day:02d}"
    m, day = str(d.month), str(d.day)
    m_full = calendar.month_name[d.month]
    m_abbr = calendar.month_abbr[d.month]

    # Ordinal suffix (1st, 2nd, 3rd, 4th, 11th-13th, ...) for legal-filing
    # date conventions like "DATED this 14th day of August, 2026."
    if 11 <= d.day % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    day_ordinal = f"{day}{suffix}"

    iso = {
        iso_date_str,                    # 2025-01-01
        iso_date_str.replace("-", "/"),  # 2025/01/01
    }
    numeric_us = set()
    # US numeric: 01/01/2025, 1/1/2025, 01-01-2025, 1-1-2025
    for sep in ("/", "-"):
        numeric_us.add(f"{mm}{sep}{dd}{sep}{yr}")
        numeric_us.add(f"{m}{sep}{day}{sep}{yr}")
    textual = set()
    ordinal = set()
    # Textual: January 1, 2025 / Jan 1, 2025 (with/without comma)
    for name in (m_full, m_abbr):
        textual.add(f"{name} {day}, {yr}")
        textual.add(f"{name} {dd}, {yr}")
        textual.add(f"{name} {day} {yr}")
        textual.add(f"{name} {dd} {yr}")
        # Ordinal legal-filing convention: "this 14th day of August, 2026"
        ordinal.add(f"{day_ordinal} day of {name}, {yr}")
        ordinal.add(f"{day_ordinal} day of {name} {yr}")
        ordinal.add(f"{name} {day_ordinal}, {yr}")
        ordinal.add(f"{name} {day_ordinal} {yr}")

    return {"iso": iso, "numeric-us": numeric_us, "textual": textual, "ordinal": ordinal}


def _date_appears_in_text(iso_date_str: str, text: str) -> bool:
    """Return True if the ISO date appears in `text` in any common format.

    The LLM is instructed to extract only dates stated verbatim in the document.
    If the date it returned cannot be located in the text — e.g. an invented
    placeholder like 2025-01-01 — it is a hallucination and must be rejected.
    """
    try:
        families = _date_variant_families(iso_date_str)
    except (TypeError, ValueError):
        return False

    haystack = text.lower()
    return any(
        v.lower() in haystack
        for variants in families.values()
        for v in variants
    )


def _nearest_numeric_span(text: str, iso_date_str: str, radius: int = 80) -> str:
    """Best-effort ±radius-char span around the nearest plausible miss location.

    Looks for the date's year, then day, as a standalone number in `text`; if
    neither is found, falls back to a truncated head of the text so the log
    line always carries *some* context to diagnose the miss against.
    """
    try:
        d = date.fromisoformat(iso_date_str)
    except (TypeError, ValueError):
        d = None

    if d is not None:
        for needle in (str(d.year), str(d.day)):
            match = re.search(rf"\b{re.escape(needle)}\b", text)
            if match:
                start = max(0, match.start() - radius)
                end = min(len(text), match.end() + radius)
                return text[start:end].strip()

    return text[: radius * 2].strip()


_MAX_LOGGED_REJECTIONS = 10


def _sanitize_events(
    data: dict[str, Any], document_text: str, doc_id: str | None = None,
) -> dict[str, Any]:
    """Nullify any extracted event_date that does not appear in the document text.

    The LLM is told to extract only verbatim dates, but it sometimes fabricates
    a plausible-looking placeholder (e.g. 2025-01-01) when no date is present.
    Deterministically discarding such a date — and escalating — keeps a fake
    date from flowing into the deterministic deadline computation (Core
    Principle: LLMs extract, deterministic code computes; "unknown" is a
    first-class output). This mirrors the Stage-2 escalation path that a
    genuinely missing date takes in pipeline.py.

    Every rejection is logged through one surface — this function — with the
    rejected value, a document identifier, a text span around the nearest
    miss location, and the variant families that were checked and failed. The
    legal date-phrasing space is unbounded (Spanish dates, unusual ordinals,
    etc.); enumerating every form is a losing game, so misses must instead be
    visible in logs/tally so each new phrasing failure is diagnosable.
    """
    doc_label = doc_id or f"text-head:{document_text[:40]!r}"
    for ev in data.get("events", []):
        ev_type = ev.get("event_type")
        if ev_type not in ALLOWED_EVENT_TYPES:
            logger.warning(
                "Coerced off-schema event_type %r to 'unknown'.", ev_type,
            )
            ev["event_type"] = "unknown"
        ev_date = ev.get("event_date")
        if not ev_date:
            continue
        if not _date_appears_in_text(ev_date, document_text):
            span = _nearest_numeric_span(document_text, ev_date)
            families_checked = ", ".join(sorted(_date_variant_families(ev_date))) \
                if isinstance(ev_date, str) else "n/a (invalid iso string)"
            logger.warning(
                "Rejected event_date %r not found in document text (doc=%s, "
                "variant_families_checked=[%s], span=%r) — likely "
                "hallucination; nullifying and escalating.",
                ev_date, doc_label, families_checked, span,
            )
            rejected = data.setdefault("rejected_dates", [])
            if len(rejected) < _MAX_LOGGED_REJECTIONS:
                rejected.append({
                    "event_date": ev_date,
                    "doc": doc_label,
                    "span": span,
                    "variant_families_checked": families_checked,
                })
            ev["event_date"] = None
            ev["confidence"] = 0.0
            data["escalation_needed"] = True
            note = (
                f"Extractor returned a date ({ev_date}) that does not appear in "
                "the document; it has been discarded as a likely hallucination."
            )
            existing = data.get("escalation_reason") or ""
            data["escalation_reason"] = f"{existing} {note}".strip()
    return data


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_schema(data: Any) -> list[str]:
    """Return a list of schema errors; empty list means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root is not an object"]
    if "events" not in data:
        errors.append("missing 'events' key")
    elif not isinstance(data["events"], list):
        errors.append("'events' is not an array")
    else:
        allowed_types = KNOWN_DOCUMENT_TYPES
        for i, ev in enumerate(data["events"]):
            if not isinstance(ev, dict):
                errors.append(f"events[{i}] is not an object")
                continue
            for required in ("event_type", "event_date", "service_method",
                             "document_type", "raw_text_excerpt", "confidence"):
                if required not in ev:
                    errors.append(f"events[{i}] missing '{required}'")
            doc_type = ev.get("document_type", "")
            if doc_type not in allowed_types:
                errors.append(f"events[{i}].document_type {doc_type!r} not in allowed set")
            conf = ev.get("confidence")
            if conf is not None and not (0.0 <= float(conf) <= 1.0):
                errors.append(f"events[{i}].confidence {conf!r} out of range [0,1]")
    return errors


async def extract_trigger_events(document_text: str) -> dict[str, Any]:
    """Call the LLM to extract trigger events from document text.

    Returns a validated dict with 'events', 'escalation_needed',
    'escalation_reason'. Retries once on schema failure; escalates on second.
    """
    client = _get_client()
    # Truncate once so the model and the sanitization guard see the same text.
    text_slice = document_text[:15000]
    prompt = (
        f"Extract trigger events from this legal document:\n\n"
        f"{text_slice}"
    )

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            data = json.loads(_strip_fences(raw))
            errors = _validate_schema(data)
            if not errors:
                return _sanitize_events(data, text_slice)
            logger.warning(
                "extract_trigger_events schema errors (attempt %d): %s",
                attempt + 1, errors,
            )
        except json.JSONDecodeError as e:
            logger.warning("extract_trigger_events JSON parse failed (attempt %d): %s", attempt + 1, e)
        except Exception as e:
            logger.error("extract_trigger_events LLM call failed: %s", e)
            break

    # Both attempts failed — return escalation signal
    return {
        "events": [],
        "escalation_needed": True,
        "escalation_reason": (
            "Could not extract valid trigger events from this document after 2 attempts. "
            "Manual review required."
        ),
    }
