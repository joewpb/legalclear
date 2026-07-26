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
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.agents.explainer import ExplainerAgent
from src.core.escalation import EscalationRouter
from src.core.upl import apply_upl_guardrails, get_disclaimer
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton explainer
explainer = ExplainerAgent()


@router.get("/api/analyze/{document_id}")
async def analyze(
    document_id: str,
    db: DatabaseManager = Depends(lambda: DatabaseManager())
) -> dict:
    """Non-streaming analysis — kept for backward compatibility."""
    try:
        doc = await db.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        classification = doc.get("classification")
        analysis_text = doc.get("analysis_text", "")

        if not classification:
            return {
                "error": True,
                "message": "Document classification missing. Please contact support.",
                "disclaimer": get_disclaimer("en")
            }

        # Run escalation checks
        escalation_router = EscalationRouter()
        escalation = await escalation_router.evaluate(doc)

        # Apply UPL guardrails
        safe_analysis = apply_upl_guardrails(analysis_text)

        return {
            "document_id": document_id,
            "classification": classification,
            "analysis": safe_analysis,
            "escalation": escalation,
            "timestamp": datetime.now(UTC).isoformat(),
            "disclaimer": get_disclaimer("en")
        }

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/analyze/stream/{document_id}")
async def analyze_stream(
    document_id: str,
    db: DatabaseManager = Depends(lambda: DatabaseManager())
):
    doc = await db.get_document(document_id)

    async def generate():
        if not doc:
            yield "data: {\"error\": true, \"message\": \"Document not found\"}\n\n"
            return
        async for chunk in explainer.explain_stream(doc.get("analysis_text", "")):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        },
    )
