"""Module 4 — Discovery Motion router.

POST /api/discovery/analyze — single-file upload, SSE streaming.
"""

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.agents.discovery_motion import DiscoveryMotionAnalyzer
from src.api.limiter import limiter

router = APIRouter(prefix="/api/discovery")
_analyzer = DiscoveryMotionAnalyzer()


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_discovery(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en"),
):
    """Analyze a Florida Motion for Discovery (PDF or image) with streaming SSE."""

    content = await file.read()

    async def _stream():
        async for chunk in _analyzer.analyze_stream(
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
