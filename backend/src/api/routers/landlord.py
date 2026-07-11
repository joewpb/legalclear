"""Landlord/Tenant FL router — Phase 18, wired to PacketBuilder in Phase 23.

Source: phases/source/PHASE_18_landlord_tenant.md + PHASE_23_packet_builder.md.

Three sub-flow generators (deposit / repairs / eviction) each call
PacketBuilder with the corresponding packet_type (landlord_deposit /
landlord_repairs / landlord_eviction). Each cover sheet template carries
the correct FL statute reference (§83.49 / §83.56(1) / §83.60) in the
"summary" + "what happens next" blocks rendered from instructions_*.json.

Path note: source put this at backend/src/api/routes/landlord.py; repo
location is backend/src/api/routers/ (see Phase 10 divergence). HTTP
endpoints unchanged.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routers.packet import build_packet_with_checkout
from src.services.packet_builder import PacketRequest

router = APIRouter(prefix="/api/landlord")


class DepositRequest(BaseModel):
    move_out_date: str
    deposit_amount: float
    current_address: str
    landlord_name: str
    landlord_address: str
    reason_given: Optional[str] = None
    tenant_response: Optional[str] = None
    county: str = "Miami-Dade"
    language: str = "en"
    user_id: Optional[str] = None


class RepairsRequest(BaseModel):
    property_address: str
    issue_type: str
    issue_description: str
    prior_communication: str
    tenant_intent: str
    county: str = "Miami-Dade"
    language: str = "en"
    user_id: Optional[str] = None


class EvictionRequest(BaseModel):
    eviction_type: str
    notice_type: str
    notice_date: str
    defenses: List[str]
    county: str = "Miami-Dade"
    language: str = "en"
    user_id: Optional[str] = None


async def _build(packet_type: str, req: BaseModel, county: str, language: str, user_id: Optional[str]):
    try:
        return await build_packet_with_checkout(
            PacketRequest(
                packet_type=packet_type,  # type: ignore[arg-type]
                language=language if language in ("en", "es") else "en",
                county=county,
                user_id=user_id or "anon",
                tile_data=req.model_dump(exclude={"language", "user_id"}),
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Packet build failed: {exc}"
        )


@router.post("/deposit/generate")
async def gen_deposit(req: DepositRequest):
    return await _build("landlord_deposit", req, req.county, req.language, req.user_id)


@router.post("/repairs/generate")
async def gen_repairs(req: RepairsRequest):
    return await _build("landlord_repairs", req, req.county, req.language, req.user_id)


@router.post("/eviction/generate")
async def gen_eviction(req: EvictionRequest):
    return await _build("landlord_eviction", req, req.county, req.language, req.user_id)
