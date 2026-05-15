"""Landlord/Tenant FL router — Phase 18.

Source: phases/source/PHASE_18_landlord_tenant.md

Three sub-flow generators (deposit / repairs / eviction), each returning
the correct FL statute reference (§83.49 / §83.56(1) / §83.60). Real
packet generation lands in Phase 23.

Path note: source put this at backend/src/api/routes/landlord.py;
repo location is backend/src/api/routers/ (see Phase 10 divergence).
HTTP endpoints unchanged.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/landlord")


class DepositRequest(BaseModel):
    move_out_date: str
    deposit_amount: float
    current_address: str
    landlord_name: str
    landlord_address: str
    reason_given: Optional[str] = None
    tenant_response: Optional[str] = None


class RepairsRequest(BaseModel):
    property_address: str
    issue_type: str
    issue_description: str
    prior_communication: str
    tenant_intent: str


class EvictionRequest(BaseModel):
    eviction_type: str
    notice_type: str
    notice_date: str
    defenses: List[str]


@router.post("/deposit/generate")
async def gen_deposit(req: DepositRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Demand for Return of Security Deposit",
        "document_url": None,
        "delivery_instructions": "Send via certified mail with return receipt. Keep a copy.",
        "applicable_statute": "FL §83.49",
        "deadlines": [
            "Landlord has 15 days from receipt to respond if claim was made",
            "30-day landlord-notice window may have already elapsed",
        ],
    }


@router.post("/repairs/generate")
async def gen_repairs(req: RepairsRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "7-Day Notice of Noncompliance with Opportunity to Cure",
        "document_url": None,
        "delivery_instructions": "Send via certified mail. Wait 7 days before further action.",
        "applicable_statute": "FL §83.56(1)",
        "deadlines": [
            "Landlord has 7 days to cure",
            "After 7 days, tenant may withhold rent or terminate",
        ],
    }


@router.post("/eviction/generate")
async def gen_eviction(req: EvictionRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Answer to Eviction Complaint",
        "document_url": None,
        "delivery_instructions": "File with the court within 5 business days of being served. Pay any disputed rent into the court registry.",
        "applicable_statute": "FL §83.60",
        "deadlines": [
            "5 business days from service to file answer",
            "Disputed rent must be deposited with court registry",
        ],
    }
