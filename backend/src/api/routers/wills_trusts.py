"""Wills & Trusts router — Module 6.

POST /api/wills-trusts/explain
  - Body: { "situation": string, "sub_type": string, "language": "en"|"es" }
  - sub_type: will | trust | probate | draft_will | unknown
  - Returns: SSE streaming response
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.wills_trusts import WillsTrustsExplainer
from src.api.limiter import limiter

router = APIRouter(prefix="/api/wills-trusts")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_explainer = WillsTrustsExplainer()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_SUB_TYPES = frozenset({
    "will",
    "trust",
    "probate",
    "draft_will",
    "unknown",
})


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class WillsTrustsExplainRequest(BaseModel):
    situation: str = Field(..., min_length=1, max_length=8000)
    sub_type: str = Field(default="unknown", pattern="^(will|trust|probate|draft_will|unknown)$")
    language: str = Field(default="en", pattern="^(en|es)$")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/explain")
@limiter.limit("10/minute")
async def wills_trusts_explain(request: Request, body: WillsTrustsExplainRequest = Body(...)):
    """Stream a wills/trusts/probate explanation via SSE."""

    async def _stream():
        async for chunk in _explainer.explain(
            situation=body.situation,
            sub_type=body.sub_type,
            language=body.language,
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
