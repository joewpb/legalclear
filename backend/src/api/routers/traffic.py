"""Traffic / Tickets FL router — Phase 20.

Source: phases/source/PHASE_20_traffic.md

Scaffolds the Contest path: returns a placeholder hearing-request packet
with a 30-day filing deadline and a list of preparation tips. Pay and
traffic-school paths are entirely frontend (links out to county clerk
portals and FLHSMV); they don't hit this router. Real Claude-generated
output lands in Phase 23.

Path note: source put this at backend/src/api/routes/traffic.py; repo
location is backend/src/api/routers/ (see Phase 10 divergence). HTTP
endpoints unchanged.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/traffic")


class TrafficRequest(BaseModel):
    citation_type: str
    citation_number: str
    issue_date: str
    county: str
    chosen_path: str  # "pay" | "school" | "contest"


@router.post("/generate")
async def gen_traffic(req: TrafficRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Request for Court Hearing",
        "document_url": None,
        "filing_deadline_days": 30,
        "filing_location": f"{req.county} County Clerk of Courts",
        "hearing_preparation_tips": [
            "Request the officer's notes via discovery",
            "Photograph the location of the alleged violation",
            "Subpoena any witnesses if applicable",
            "Bring a copy of your driving record",
        ],
    }
