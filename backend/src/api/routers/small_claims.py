"""Small Claims FL router — Phase 16.

Source: phases/source/PHASE_16_small_claims.md

Path note: source spec puts this at backend/src/api/routes/small_claims.py,
but the repo's backend/src/api/routes.py is a file (Phase 10 divergence).
Routers live in backend/src/api/routers/ instead. HTTP endpoint is
identical — /api/small-claims/generate — set by the router prefix.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

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


@router.post("/generate")
async def generate_small_claims(req: SmallClaimsRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "forms": [
            {
                "name": "Statement of Claim (Form 7.301)",
                "url": "https://www.flcourts.gov/content/download/218019/file/7.301.pdf",
            },
            {
                "name": "Summons (Form 7.321)",
                "url": "https://www.flcourts.gov/content/download/218020/file/7.321.pdf",
            },
        ],
        "filing_instructions": f"File at {req.county} County Clerk of Courts.",
        "filing_fee_usd": 175,
        "clerk_url": "https://www.flclerks.com/",
        "service_of_process_options": ["Sheriff", "Certified Mail", "Private Process Server"],
    }
