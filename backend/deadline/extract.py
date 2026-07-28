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
      "event_type": "served" | "filed" | "issued" | "rendered" | "unknown",
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
7. NEVER invent or guess a date. Do NOT output placeholder dates such as
   2025-01-01, 1970-01-01, or any January 1 / round-number date. Every
   non-null event_date MUST be a date that appears verbatim in the document
   text — if no date is stated, set event_date to null. The raw_text_excerpt
   must contain that exact date. A returned date that cannot be found in the
   document is treated as a hallucination and will be discarded.
"""


def _date_appears_in_text(iso_date_str: str, text: str) -> bool:
    """Return True if the ISO date appears in `text` in any common format.

    The LLM is instructed to extract only dates stated verbatim in the document.
    If the date it returned cannot be located in the text — e.g. an invented
    placeholder like 2025-01-01 — it is a hallucination and must be rejected.
    """
    try:
        d = date.fromisoformat(iso_date_str)
    except (TypeError, ValueError):
        return False

    haystack = text.lower()
    yr = str(d.year)
    mm, dd = f"{d.month:02d}", f"{d.day:02d}"
    m, day = str(d.month), str(d.day)
    m_full = calendar.month_name[d.month]
    m_abbr = calendar.month_abbr[d.month]

    variants = {
        iso_date_str,                        # 2025-01-01
        iso_date_str.replace("-", "/"),      # 2025/01/01
    }
    # US numeric: 01/01/2025, 1/1/2025, 01-01-2025, 1-1-2025
    for sep in ("/", "-"):
        variants.add(f"{mm}{sep}{dd}{sep}{yr}")
        variants.add(f"{m}{sep}{day}{sep}{yr}")
    # Textual: January 1, 2025 / Jan 1, 2025 (with/without comma)
    for name in (m_full, m_abbr):
        variants.add(f"{name} {day}, {yr}")
        variants.add(f"{name} {dd}, {yr}")
        variants.add(f"{name} {day} {yr}")
        variants.add(f"{name} {dd} {yr}")

    return any(v.lower() in haystack for v in variants)


def _sanitize_events(data: dict[str, Any], document_text: str) -> dict[str, Any]:
    """Nullify any extracted event_date that does not appear in the document text.

    The LLM is told to extract only verbatim dates, but it sometimes fabricates
    a plausible-looking placeholder (e.g. 2025-01-01) when no date is present.
    Deterministically discarding such a date — and escalating — keeps a fake
    date from flowing into the deterministic deadline computation (Core
    Principle: LLMs extract, deterministic code computes; "unknown" is a
    first-class output). This mirrors the Stage-2 escalation path that a
    genuinely missing date takes in pipeline.py.
    """
    for ev in data.get("events", []):
        ev_date = ev.get("event_date")
        if not ev_date:
            continue
        if not _date_appears_in_text(ev_date, document_text):
            logger.warning(
                "Rejected event_date %r not found in document text — likely "
                "hallucination; nullifying and escalating.", ev_date,
            )
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
