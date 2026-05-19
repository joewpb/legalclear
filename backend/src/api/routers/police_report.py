"""Police Report Analyzer router — Phase 21.

Source: phases/source/PHASE_21_police_report.md

Multipart upload endpoint: takes a required primary police report plus up
to 4 supplementary documents (witness statements, body cam transcript,
dispatch log). Reuses the Phase 02 ingestion pipeline for PDF/OCR/text
extraction, then hands the extracted text to the new Phase 21 Scanner
Agent.

Path note: source put this at backend/src/api/routes/police_report.py;
repo location is backend/src/api/routers/ (Phase 10 divergence).

Phase 02 API note: source imports `extract` from `services/pdf_processor`;
repo equivalent is `ingest_document(file_bytes, filename) -> dict` at
`src/ingestion/__init__.py` (Part A divergence #4 in the ledger). We
import the real symbol — the source spec explicitly permits this.

Failure policy: any per-file extraction error is caught and the file is
recorded with empty text. The Scanner Agent itself is fail-soft (returns
empty findings on any exception). The endpoint therefore returns 200
with `findings: []` rather than 500 when ingestion or analysis fails.
"""
from __future__ import annotations

import logging
import traceback
from typing import List

from fastapi import APIRouter, File, UploadFile

from src.agents.scanner import extract_case_context, scan_documents
from src.ingestion import ingest_document

router = APIRouter(prefix="/api/police-report")
logger = logging.getLogger(__name__)


@router.post("/analyze")
async def analyze_report(files: List[UploadFile] = File(...)):
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
        except Exception as e:  # noqa: BLE001 — keep endpoint stable on malformed PDFs
            logger.warning(
                "police-report extraction failed for %s (%s)\n%s",
                getattr(f, "filename", "?"),
                type(e).__name__,
                traceback.format_exc(),
            )
            extracted.append({"filename": getattr(f, "filename", "upload.pdf") or "upload.pdf", "text": ""})

    result = await scan_documents(extracted)
    case_context = await extract_case_context(extracted)
    return {
        "findings": result["findings"],
        "documents_analyzed": result["meta"]["documents_analyzed"],
        "case_context": case_context,
    }
