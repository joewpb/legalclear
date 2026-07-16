"""Traffic / Tickets FL router — Phase 20, wired to PacketBuilder in Phase 23.

Source: phases/source/PHASE_20_traffic.md + PHASE_23_packet_builder.md.

Contest path builds a packet with packet_type=traffic. Pay and
traffic-school paths are entirely frontend (links to county clerk
portals and FLHSMV); they don't hit this router.

Path note: source put this at backend/src/api/routes/traffic.py; repo
location is backend/src/api/routers/ (see Phase 10 divergence). HTTP
endpoints unchanged.
"""
import logging
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routers.packet import build_packet_with_checkout
from src.services.packet_builder import PacketRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/traffic")


class TrafficRequest(BaseModel):
    citation_type: str
    citation_number: str
    issue_date: str
    county: str
    chosen_path: str  # "pay" | "school" | "contest"
    language: str = "en"
    user_id: Optional[str] = None


@router.post("/generate")
async def gen_traffic(req: TrafficRequest):
    try:
        return await build_packet_with_checkout(
            PacketRequest(
                packet_type="traffic",
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
            "Traffic packet build failed:\n%s",
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500, detail=f"Packet build failed: {exc}"
        )
