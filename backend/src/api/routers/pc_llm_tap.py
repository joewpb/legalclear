"""I-8 — LLM-on-tap router (Phase I finale, 2026-08-23).

Every endpoint here is an EXPLICIT user action — the model runs only
because the user tapped a button, never as part of a pipeline. All taps are
rate-limited and all outputs carry the standard disclaimer.

No tap may compute deadlines, decide coverage, or predict settlements —
that contract lives in the agent prompts and is tested in
tests/test_pc_llm_tap.py.
"""

from fastapi import APIRouter, File, Form, Request, UploadFile

from src.agents.pc_llm_tap import PcLlmTap
from src.api.limiter import limiter

router = APIRouter(prefix="/api/property-casualty/tap")
_tap = PcLlmTap()


@router.post("/explain-letter")
@limiter.limit("10/minute")
async def explain_letter(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en"),
):
    file_bytes = await file.read()
    return await _tap.explain_letter(file_bytes, file.filename or "letter", language)


@router.post("/describe-item")
@limiter.limit("10/minute")
async def describe_item(
    request: Request,
    notes: str = Form(...),
    language: str = Form(default="en"),
):
    return await _tap.describe_item(notes, language)


@router.post("/notes-to-demand")
@limiter.limit("10/minute")
async def notes_to_demand(
    request: Request,
    notes: str = Form(...),
    language: str = Form(default="en"),
):
    return await _tap.notes_to_demand(notes, language)


@router.post("/define-term")
@limiter.limit("10/minute")
async def define_term(
    request: Request,
    term: str = Form(...),
    language: str = Form(default="en"),
):
    return await _tap.define_term(term, language)


@router.post("/classify-document")
@limiter.limit("10/minute")
async def classify_document(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en"),
):
    file_bytes = await file.read()
    return await _tap.classify_document(file_bytes, file.filename or "document", language)
