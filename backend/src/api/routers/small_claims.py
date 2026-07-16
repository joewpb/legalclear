"""Small Claims FL router — Phase 16 (filing wizard) + Module 1 (explainer).

Source: phases/source/PHASE_16_small_claims.md + PHASE_23_packet_builder.md
       + v3 Module 1 (small claims streaming explainer).

Path note: source spec puts this at backend/src/api/routes/small_claims.py,
but the repo's backend/src/api/routes.py is a file (Phase 10 divergence).
Routers live in backend/src/api/routers/ instead. HTTP endpoint is
identical — /api/small-claims/… — set by the router prefix.

Phase 23 wiring: /generate now returns a packet_id + Stripe checkout URL
instead of the prior scaffold JSON. The frontend ReviewStep navigates to
/filing-packet/:packetId on receiving the response.

Module 1 wiring: /explain streams a plain-English small-claims explanation
via SSE from claude-sonnet-4-6.  The intake router feeds it entities from
the user's situation description.
"""
import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.small_claims import SmallClaimsExplainer
from src.api.routers.packet import build_packet_with_checkout
from src.api.routes import limiter
from src.services.packet_builder import PacketRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/small-claims")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_explainer = SmallClaimsExplainer()

# ---------------------------------------------------------------------------
# Phase 16 — Filing wizard (existing)
# ---------------------------------------------------------------------------


class SmallClaimsRequest(BaseModel):
    claim_type: str
    amount: float
    defendant_type: str
    defendant_name: str
    defendant_address: str
    defendant_phone: Optional[str] = None
    defendant_email: Optional[str] = None
    county: str
    language: str = "en"
    user_id: Optional[str] = None


@router.post("/generate")
@limiter.limit("10/minute")
async def generate_small_claims(request: Request, req: SmallClaimsRequest):
    try:
        return await build_packet_with_checkout(
            PacketRequest(
                packet_type="small_claims",
                language=req.language if req.language in ("en", "es") else "en",
                county=req.county,
                user_id=req.user_id or "anon",
                tile_data=req.model_dump(exclude={"language", "user_id"}),
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Small claims packet build failed:\n%s",
            traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Packet build failed: {exc}")


# ---------------------------------------------------------------------------
# Module 1 — AI Explainer (new)
# ---------------------------------------------------------------------------


class ExplainRequest(BaseModel):
    entities: dict = Field(default_factory=dict, description="Key-value pairs from the intake classifier")
    language: str = Field(default="en", pattern="^(en|es)$")


@router.post("/explain")
@limiter.limit("10/minute")
async def explain_small_claims(request: Request, payload: ExplainRequest = Body(...)):
    """Stream a plain-English Florida small-claims explanation via SSE."""

    async def _stream():
        async for chunk in _explainer.explain_stream(
            entities=payload.entities,
            language=payload.language,
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
