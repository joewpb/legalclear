"""Module 0 — AI Intake Router.

Classifies a user's plain-English situation description into one of the
LegalClear v3 module routes using claude-haiku-4-5-20251001.
"""

import json
import logging
import traceback

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["intake"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

VALID_MODULES = [
    "small_claims",
    "criminal_procedure",
    "police_report",
    "discovery_motion",
    "property_casualty",
    "wills_trusts",
    "unknown",
]

VALID_SUB_TYPES = [
    "first_party_property",
    "insurance_bad_faith",
    "premises_liability",
    "will",
    "trust",
    "probate",
    "draft_will",
    "unknown",
]


class IntakeRequest(BaseModel):
    situation: str = Field(..., min_length=1, max_length=8000)
    language: str = Field(default="en", pattern="^(en|es)$")


class IntakeResponse(BaseModel):
    module: str
    sub_type: str | None = None
    entities: dict = Field(default_factory=dict)
    confidence: float
    clarifying_question: str | None = None
    disclaimer: str


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a legal situation classifier for Florida pro se "
    "litigants. Classify the situation into exactly one of: "
    "small_claims, criminal_procedure, police_report, "
    "discovery_motion, property_casualty, wills_trusts, unknown. "
    "For property_casualty also identify sub_type: "
    "first_party_property, insurance_bad_faith, or premises_liability. "
    "first_party_property = dispute under the claimant's OWN policy "
    "for property damage (hurricane/wind/water/roof/fire/theft) — "
    "underlying theory is breach of contract. A denied claim stays "
    "first_party_property until an explicit Civil Remedy Notice or "
    "bad-faith posture appears. insurance_bad_faith = the separate, "
    "downstream § 624.155 track, gated by a CRN — it FOLLOWS a "
    "first-party dispute, it is not a synonym. "
    "For wills_trusts also identify sub_type: "
    "will, trust, probate, draft_will, or unknown. "
    "Key indicators for wills_trusts: will, trust, estate, "
    "probate, executor, beneficiary, inheritance, death, "
    "assets after death, living will, power of attorney. "
    "Extract key entities (amounts, charge types, parties, "
    "document types, incident types). "
    "Return valid JSON only — no markdown, no preamble: "
    "{ module, sub_type, entities, confidence, "
    "clarifying_question }"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitize_module(value: str) -> str:
    """Coerce the classified module into one of the valid slots."""
    if value in VALID_MODULES:
        return value
    return "unknown"


def _sanitize_sub_type(value: str | None) -> str | None:
    """Coerce sub_type or return None / unknown."""
    if value in VALID_SUB_TYPES:
        return value
    if value is not None:
        return "unknown"
    return None


# ---------------------------------------------------------------------------
# Client — reuses the same Anthropic key already configured
# ---------------------------------------------------------------------------

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=2, timeout=30.0)
_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/intake", response_model=IntakeResponse)
async def intake(payload: IntakeRequest = Body(...)) -> IntakeResponse:
    """Classify a plain-English situation description and route to a module."""

    user_prompt = (
        f"Language: {payload.language}\n\n"
        f"Situation: {payload.situation}"
    )

    message_content = (
        "Return ONLY a JSON object. No markdown, no preamble. "
        + user_prompt
    )

    module = "unknown"
    sub_type: str | None = None
    entities: dict = {}
    confidence = 0.0
    clarifying_question: str | None = None

    for attempt in range(2):
        try:
            response = await _client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Return ONLY a JSON object. No other text. "
                            + user_prompt
                            if attempt > 0
                            else message_content
                        ),
                    }
                ],
            )

            raw = response.content[0].text
            parsed = json.loads(strip_markdown_fences(raw))

            module = _sanitize_module(parsed.get("module", "unknown"))
            sub_type = _sanitize_sub_type(parsed.get("sub_type"))
            entities = parsed.get("entities", {}) or {}
            confidence = float(parsed.get("confidence", 0.0))
            clarifying_question = parsed.get("clarifying_question")

            # Low confidence → force unknown with clarifying question
            if confidence < 0.70:
                module = "unknown"
                if not clarifying_question:
                    clarifying_question = (
                        "Could you share more about your situation "
                        "so the right information can be found?"
                    )

            # Property casualty without sub_type gets unknown
            if module == "property_casualty" and sub_type is None:
                sub_type = "unknown"

            break  # success — don't retry

        except Exception:
            logger.error(
                "Intake classification attempt %d failed: %s\n%s",
                attempt + 1,
                traceback.format_exc(),
                traceback.format_exc(),
            )

    disclaimer = get_disclaimer(payload.language)

    return IntakeResponse(
        module=module,
        sub_type=sub_type,
        entities=entities,
        confidence=confidence,
        clarifying_question=clarifying_question,
        disclaimer=disclaimer,
    )
