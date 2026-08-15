"""Phase 4 — Deadline Engine HTTP endpoints."""

import logging

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import require_api_key
from src.core.upl import apply_disclaimer
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/deadline", tags=["deadline"])
db = DatabaseManager()


@router.post("/analyze/{document_id}", dependencies=[Depends(require_api_key)])
async def analyze_document(document_id: str):
    """Run the deadline pipeline on an already-ingested document.

    Fetches document_text from the DB, runs Stage 1 (LLM extraction) and
    Stage 2 (deterministic computation), writes trigger_events and deadlines.
    """
    from deadline.pipeline import run_deadline_pipeline

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

    result = await run_deadline_pipeline(document_id, text, db)
    return apply_disclaimer(result, lang="en")


@router.get("/{document_id}/deadlines")
async def get_deadlines(document_id: str, session_id: Optional[str] = None):
    """Return all computed deadlines for a document, ordered by due_date."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = db.get_document(document_id)
    if not doc or not session_id or doc.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = (db.client.table("deadlines")
                  .select("id,label,due_date,governing_rule,consequence_if_missed,"
                          "severity,confidence,escalation_recommended,"
                          "computation_trace,reminder_state,created_at")
                  .eq("document_id", document_id)
                  .order("due_date")
                  .execute())
        return apply_disclaimer({"deadlines": result.data or []}, lang="en")
    except Exception as e:
        logger.error("get_deadlines failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve deadlines") from e


@router.get("/{document_id}/trigger-events")
async def get_trigger_events(document_id: str, session_id: Optional[str] = None):
    """Return extracted trigger events for a document."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = db.get_document(document_id)
    if not doc or not session_id or doc.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = (db.client.table("trigger_events")
                  .select("*")
                  .eq("document_id", document_id)
                  .order("created_at")
                  .execute())
        return apply_disclaimer({"trigger_events": result.data or []}, lang="en")
    except Exception as e:
        logger.error("get_trigger_events failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve trigger events") from e
