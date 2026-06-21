"""Police Report Analyzer router — Phase 21 (batch) + Module 3 (streaming v2).

POST /api/police-report/analyze       — Module 3: single file, SSE streaming
POST /api/police-report/analyze/batch — Phase 21: multi-file, non-streaming (legacy)
"""

from __future__ import annotations

import logging
import traceback
from typing import List

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from src.agents.police_report_v2 import PoliceReportAnalyzerV2
from src.agents.scanner import extract_case_context, scan_documents
from src.ingestion import ingest_document

router = APIRouter(prefix="/api/police-report")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_analyzer_v2 = PoliceReportAnalyzerV2()

# ---------------------------------------------------------------------------
# Module 3 — Streaming single-file analysis
# ---------------------------------------------------------------------------


@router.post("/analyze")
async def analyze_report_v3(
    file: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Analyze a single police report (PDF or image) with streaming SSE."""

    content = await file.read()

    async def _stream():
        async for chunk in _analyzer_v2.analyze_stream(
            file_bytes=content,
            filename=file.filename or "upload.pdf",
            language=language if language in ("en", "es") else "en",
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Phase 21 — Multi-file batch analysis (legacy, non-streaming)
# ---------------------------------------------------------------------------


@router.post("/analyze/batch")
async def analyze_report_batch(files: List[UploadFile] = File(...)):
    """Multi-file police report analysis — Phase 21 legacy endpoint."""
    extracted: list[dict] = []
    for f in files:
        try:
            content = await f.read()
            result = await ingest_document(content, f.filename or "upload.pdf")
            extracted.append(
                {
                    "filename": f.filename or "upload.pdf",
                    "text": result.get("text", "") if isinstance(result, dict) else "",
                }
            )
        except Exception:
            logger.warning(
                "police-report extraction failed for %s (%s)\n%s",
                getattr(f, "filename", "?"),
                type(Exception).__name__,
                traceback.format_exc(),
            )
            extracted.append(
                {
                    "filename": getattr(f, "filename", "upload.pdf") or "upload.pdf",
                    "text": "",
                }
            )

    result = await scan_documents(extracted)
    case_context = await extract_case_context(extracted)
    return {
        "findings": result["findings"],
        "documents_analyzed": result["meta"]["documents_analyzed"],
        "case_context": case_context,
        "risk_analysis": result.get("risk_analysis"),
    }
