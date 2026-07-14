"""Phase 5 — Document Triage endpoints."""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from src.api.dependencies import require_api_key
from src.core.upl import apply_disclaimer
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/triage", tags=["triage"])
db = DatabaseManager()


@router.post("/classify/{document_id}", dependencies=[Depends(require_api_key)])
async def classify_document(document_id: str):
    """Classify a document and return routing instructions.

    Runs the triage classifier, writes the result to documents.classification,
    and returns routing: which deadline rules apply, which form tags to surface,
    and whether the user needs to confirm the classification before proceeding.

    Criminal/expungement documents are immediately escalated.
    Low-confidence classifications are flagged for human confirmation —
    they will NOT auto-trigger deadline computation.
    """
    from triage.classify import classify_document as _classify
    from triage.router import route

    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    text = doc.get("document_text") or ""
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Document has no extractable text. Upload the document first."
        )

    classification = await _classify(text)
    routing = route(classification)

    # Write classification to documents.classification
    if db.client is not None:
        try:
            db.client.table("documents").update(
                {"classification": classification}
            ).eq("id", document_id).execute()
        except Exception as e:
            logger.error("Failed to write classification for %s: %s", document_id, e)

    # Surface relevant court forms from catalog (active only)
    suggested_forms: list[dict] = []
    if routing["suggested_form_tags"] and db.client is not None:
        try:
            for tag in routing["suggested_form_tags"]:
                # 'published' is the current status vocabulary (Phase 10);
                # 'active' kept for legacy compat — matches forms.py _SERVABLE.
                result = (db.client.table("court_forms")
                          .select("form_number,title,court_revision_date,status")
                          .in_("status", ["published", "active"])
                          .contains("situation_tags", [tag])
                          .execute())
                suggested_forms.extend(result.data or [])
            # Deduplicate by form_number
            seen = set()
            deduped = []
            for f in suggested_forms:
                if f["form_number"] not in seen:
                    seen.add(f["form_number"])
                    deduped.append(f)
            suggested_forms = deduped
        except Exception as e:
            logger.error("Form lookup failed: %s", e)

    return apply_disclaimer({
        "document_id": document_id,
        "classification": classification,
        "routing": {
            **routing,
            "suggested_forms": suggested_forms,
        },
    }, lang="en")


@router.post("/confirm/{document_id}", dependencies=[Depends(require_api_key)])
async def confirm_classification(
    document_id: str,
    document_type: str = Body(..., embed=True),
):
    """Allow a user to confirm or correct the document type.

    Called after the user selects from the dropdown on the review screen.
    Updates documents.classification.document_type and clears the
    requires_human_review flag so the deadline pipeline can proceed.
    """
    from triage.classify import VALID_DOCUMENT_TYPES as VDT
    from triage.router import (
        route,
    )

    if document_type not in VDT:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid document_type. Allowed: {VDT}"
        )
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    existing = doc.get("classification") or {}
    updated = {
        **existing,
        "document_type": document_type,
        "document_type_confidence": 1.0,   # human-confirmed
        "requires_human_review": False,
        "review_reason": None,
        "human_confirmed": True,
    }

    try:
        db.client.table("documents").update(
            {"classification": updated}
        ).eq("id", document_id).execute()
    except Exception as e:
        logger.error("confirm_classification failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not update classification")

    routing = route(updated)
    return apply_disclaimer({
        "document_id": document_id,
        "classification": updated,
        "routing": routing,
    }, lang="en")
