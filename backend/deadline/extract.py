"""LLM trigger-event extractor — Phase 4, Stage 1.

THE LLM MUST NEVER COMPUTE OR OUTPUT A DEADLINE DATE.
It extracts only what is explicitly stated in the document text.

Schema contract: one call per document → list of trigger events.
Retry once on schema-invalid output; escalate on second failure.
"""

from __future__ import annotations

import json
import logging
import re
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
"""


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
    prompt = (
        f"Extract trigger events from this legal document:\n\n"
        f"{document_text[:15000]}"
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
                return data
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
