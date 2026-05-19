"""Phase 5 — Document Triage Classifier.

LLM call that identifies what kind of legal document was uploaded and
extracts enough metadata (jurisdiction, circuit, county, case number)
to drive deadline-rule selection and court-form surfacing.

Produces legal INFORMATION (what type of document is this, what court,
what case). Never produces a legal conclusion or advice.

Output is written to documents.classification in the caller.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

CONFIDENCE_THRESHOLD = 0.70  # below this → requires_human_review

VALID_DOCUMENT_TYPES = [
    "civil_summons",
    "eviction_complaint",
    "foreclosure_complaint",
    "family_law_petition",
    "small_claims_summons",
    "motion",
    "order",
    "judgment",
    "notice_of_hearing",
    "discovery_request",
    "criminal",
    "expungement",
    "unknown",
]

SYSTEM_PROMPT = """\
You are a legal document triage classifier for Florida courts. Your only job is \
to identify what kind of legal document this is and extract key metadata from \
its text. You produce legal information — never legal advice or conclusions.

Return valid JSON with exactly these fields (no markdown, no extra keys):
{
  "document_type": "<one of the allowed types>",
  "document_type_confidence": <0.0–1.0>,
  "jurisdiction": "FL" | "<state>" | "federal" | "unknown",
  "jurisdiction_confidence": <0.0–1.0>,
  "circuit": <integer 1-20> | null,
  "circuit_confidence": <0.0–1.0>,
  "county": "<county name>" | null,
  "county_confidence": <0.0–1.0>,
  "is_criminal": true | false,
  "is_expungement": true | false,
  "case_number": "<string>" | null,
  "issuing_court": "<string>" | null,
  "notes": "<brief note about any ambiguity or unusual feature>" | null
}

Allowed document_type values:
  civil_summons         — summons to answer a civil lawsuit
  eviction_complaint    — complaint or summons for eviction/unlawful detainer
  foreclosure_complaint — complaint to foreclose a mortgage
  family_law_petition   — petition for dissolution, custody, support, etc.
  small_claims_summons  — small claims court summons or notice
  motion                — any motion filed in court
  order                 — court order (not final judgment)
  judgment              — final judgment or decree
  notice_of_hearing     — notice setting a hearing date
  discovery_request     — interrogatories, requests for production, admissions
  criminal              — any criminal charge, indictment, information, or plea
  expungement           — petition or application to expunge/seal a record
  unknown               — cannot be determined with confidence

Rules:
1. If you cannot determine a field with confidence, use null or "unknown".
2. "unknown" for document_type is always valid.
3. For is_criminal and is_expungement: set to true even if confidence is low —
   erring toward escalation is safer than missing a criminal matter.
4. Notes field: flag ambiguity only, never describe legal consequences.
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root is not an object"]
    required = ("document_type", "document_type_confidence", "jurisdiction",
                "is_criminal", "is_expungement")
    for f in required:
        if f not in data:
            errors.append(f"missing '{f}'")
    dt = data.get("document_type")
    if dt not in VALID_DOCUMENT_TYPES:
        errors.append(f"document_type {dt!r} not in allowed set")
    conf = data.get("document_type_confidence")
    if conf is not None and not (0.0 <= float(conf) <= 1.0):
        errors.append(f"document_type_confidence {conf!r} out of range")
    return errors


async def classify_document(document_text: str) -> dict[str, Any]:
    """Classify a document. Returns a validated classification dict.

    Retries once on schema failure; returns unknown classification on second.
    """
    client = _get_client()
    prompt = (
        "Classify this legal document and return the JSON schema described:\n\n"
        f"{document_text[:20000]}"
    )

    for attempt in range(2):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            data = json.loads(_strip_fences(raw))
            errors = _validate(data)
            if not errors:
                # Annotate requires_human_review based on confidence
                conf = float(data.get("document_type_confidence", 0.0))
                data["requires_human_review"] = (
                    conf < CONFIDENCE_THRESHOLD
                    or data.get("document_type") == "unknown"
                )
                data["review_reason"] = (
                    f"Classification confidence {conf:.0%} is below the "
                    f"{CONFIDENCE_THRESHOLD:.0%} threshold — please confirm the document type."
                    if data["requires_human_review"] and data.get("document_type") != "unknown"
                    else (
                        "Document type could not be determined. Please select from the dropdown."
                        if data.get("document_type") == "unknown"
                        else None
                    )
                )
                return data
            logger.warning("classify_document schema errors (attempt %d): %s", attempt + 1, errors)
        except json.JSONDecodeError as e:
            logger.warning("classify_document JSON parse failed (attempt %d): %s", attempt + 1, e)
        except Exception as e:
            logger.error("classify_document LLM call failed: %s", e)
            break

    # Fallback — return unknown classification, flag for review
    return {
        "document_type": "unknown",
        "document_type_confidence": 0.0,
        "jurisdiction": "unknown",
        "jurisdiction_confidence": 0.0,
        "circuit": None,
        "circuit_confidence": 0.0,
        "county": None,
        "county_confidence": 0.0,
        "is_criminal": False,
        "is_expungement": False,
        "case_number": None,
        "issuing_court": None,
        "notes": "Classification failed after 2 attempts.",
        "requires_human_review": True,
        "review_reason": "Could not classify document. Please select document type from the dropdown.",
    }
