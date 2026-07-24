"""Module 5 — Property & Casualty router.

POST /api/property-casualty/explain — streaming SSE.
Accepts entities + optional document upload.
"""

import json
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.agents.property_casualty import PropertyCasualtyExplainer
from src.api.limiter import limiter

router = APIRouter(prefix="/api/property-casualty")
_explainer = PropertyCasualtyExplainer()


@router.post("/explain")
@limiter.limit("10/minute")
async def explain_property_casualty(
    request: Request,
    sub_type: str = Form(default="unknown"),
    entities_json: str = Form(default="{}"),
    language: str = Form(default="en"),
    file: Optional[UploadFile] = File(default=None),
):
    """Explain a Florida property/casualty situation with optional document."""

    # Parse entities from JSON string
    try:
        entities: dict = json.loads(entities_json)
    except (json.JSONDecodeError, TypeError):
        entities = {}

    # Read optional file
    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    if file is not None:
        file_bytes = await file.read()
        filename = file.filename

    async def _stream():
        async for chunk in _explainer.explain_stream(
            sub_type=sub_type if sub_type in ("first_party_property", "insurance_bad_faith", "premises_liability", "unknown") else "unknown",
            entities=entities,
            language=language if language in ("en", "es") else "en",
            file_bytes=file_bytes,
            filename=filename,
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
