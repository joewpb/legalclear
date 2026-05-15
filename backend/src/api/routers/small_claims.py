"""Small Claims FL router — Phase 16, wired to PacketBuilder in Phase 23.

Source: phases/source/PHASE_16_small_claims.md + PHASE_23_packet_builder.md.

Path note: source spec puts this at backend/src/api/routes/small_claims.py,
but the repo's backend/src/api/routes.py is a file (Phase 10 divergence).
Routers live in backend/src/api/routers/ instead. HTTP endpoint is
identical — /api/small-claims/generate — set by the router prefix.

Phase 23 wiring: /generate now returns a packet_id + Stripe checkout URL
instead of the prior scaffold JSON. The frontend ReviewStep navigates to
/filing-packet/:packetId on receiving the response.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.api.routers.packet import build_packet_with_checkout
from src.services.packet_builder import PacketRequest

router = APIRouter(prefix="/api/small-claims")


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
async def generate_small_claims(req: SmallClaimsRequest):
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
        raise HTTPException(status_code=500, detail=f"Packet build failed: {exc}")
