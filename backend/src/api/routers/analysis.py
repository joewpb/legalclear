"""Phase 8 — Unified analysis endpoint with UPL/disclaimer layer.

This is the v2 entry point for a fully analyzed document. It:
1. Loads classification and deadlines already computed by Phases 4 & 5.
2. Runs escalation checks (Phase 8 triggers).
3. Applies disclaimers to all output fields.
4. Writes escalation result to documents.escalation.
5. Returns the full analysis with disclaimer attached.

Fallback: if classification is missing or type is unknown, the system
says so plainly and directs the user to help — it does not guess.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.config import settings
from src.core.upl import (
    ATTORNEY_REFERRAL_LINKS,
    apply_disclaimer,
    check_escalation,
    get_disclaimer,
)
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])
db = DatabaseManager()

FALLBACK_MESSAGE_EN = (
    "LegalClear was unable to safely analyze this document. "
    "The document type could not be determined with sufficient confidence, "
    "or the extraction did not produce verifiable results. "
    "Please consult a licensed Florida attorney for assistance. "
    "Free or low-cost help may be available at floridalawhelp.org."
)
FALLBACK_MESSAGE_ES = (
    "LegalClear no pudo analizar este documento de manera segura. "
    "No se pudo determinar el tipo de documento con suficiente confianza, "
    "o la extracción no produjo resultados verificables. "
    "Consulte a un abogado autorizado de Florida. "
    "Puede haber ayuda gratuita o de bajo costo en floridalawhelp.org."
)


def _require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@router.get("/{document_id}")
async def get_analysis(document_id: str):
    """Return the full v2 analysis for a document, with disclaimers applied.

    Preconditions: triage classify + deadline analyze already called.
    This endpoint is the read-only output layer — it assembles, audits,
    and presents the results with the UPL/disclaimer layer applied.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    lang = doc.get("language") or "en"
    classification = doc.get("classification") or {}
    explanation = doc.get("explanation") or {}
    form_guide = doc.get("form_guide") or {}
    escalation_stored = doc.get("escalation") or {}

    # Load deadlines
    deadlines: list[dict] = []
    try:
        result = (db.client.table("deadlines")
                  .select("id,label,due_date,governing_rule,consequence_if_missed,"
                          "severity,confidence,escalation_recommended,computation_trace")
                  .eq("document_id", document_id)
                  .order("due_date")
                  .execute())
        deadlines = result.data or []
    except Exception as e:
        logger.error("Failed to load deadlines for %s: %s", document_id, e)

    # Determine disclaimer level and run escalation
    escalation = check_escalation(classification, deadlines, lang=lang)

    # Fallback: if no useful classification and no deadlines, decline rather than guess
    doc_type = classification.get("document_type")
    is_fallback = (
        not doc_type or doc_type == "unknown"
    ) and not deadlines and not explanation

    if is_fallback:
        fallback_msg = FALLBACK_MESSAGE_ES if lang == "es" else FALLBACK_MESSAGE_EN
        return {
            "document_id": document_id,
            "status": "fallback",
            "message": fallback_msg,
            "disclaimer": get_disclaimer("standard", lang),
            "attorney_referral_links": ATTORNEY_REFERRAL_LINKS.get(lang, ATTORNEY_REFERRAL_LINKS["en"]),
        }

    # Write escalation result to documents.escalation
    escalation_dict = escalation.to_dict()
    escalation_dict["evaluated_at"] = datetime.now(tz=timezone.utc).isoformat()
    try:
        db.client.table("documents").update(
            {"escalation": escalation_dict}
        ).eq("id", document_id).execute()
    except Exception as e:
        logger.error("Failed to write escalation for %s: %s", document_id, e)

    # Apply disclaimer to output fields that go to users
    disclaimer_level = escalation.disclaimer_level
    disclaimer_text = get_disclaimer(disclaimer_level, lang)

    # Build deadline output with disclaimer on each item
    deadline_output = []
    for dl in deadlines:
        deadline_output.append({
            **dl,
            "disclaimer": disclaimer_text,
        })

    # Apply disclaimer to explanation and form_guide
    explanation_with_disclaimer = apply_disclaimer(explanation, lang, disclaimer_level)
    form_guide_with_disclaimer = apply_disclaimer(form_guide, lang, disclaimer_level)

    return {
        "document_id": document_id,
        "classification": classification,
        "explanation": explanation_with_disclaimer,
        "form_guide": form_guide_with_disclaimer,
        "deadlines": deadline_output,
        "escalation": escalation_dict,
        "disclaimer": disclaimer_text,
        "attorney_referral_links": (
            ATTORNEY_REFERRAL_LINKS.get(lang, ATTORNEY_REFERRAL_LINKS["en"])
            if escalation.should_escalate else []
        ),
        "language": lang,
    }


@router.get("/forms/{form_number}/info")
async def get_form_provenance(form_number: str):
    """Return form provenance metadata (Task 4 — form provenance display).

    Every form shown to a user must display:
    - That it is the official court form
    - court_revision_date
    - last_changed_at
    - source_page_url (for attribution)
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        result = (db.client.table("court_forms")
                  .select("form_number,title,category,status,court_revision_date,"
                          "last_checked_at,last_changed_at,source_page_url,"
                          "plain_language_summary,situation_tags")
                  .eq("form_number", form_number)
                  .execute())
        if not result.data:
            raise HTTPException(status_code=404, detail="Form not found")
        form = result.data[0]
        form["provenance_statement"] = (
            f"This is the official Florida court form {form_number} published by "
            "the Florida Office of the State Courts Administrator. "
            f"Form revision date: {form.get('court_revision_date') or 'see court website'}. "
            "LegalClear serves this form from a permanent copy and verifies it weekly "
            "for changes. If this form has been updated, this page will say so."
        )
        return form
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_form_provenance failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve form info")
