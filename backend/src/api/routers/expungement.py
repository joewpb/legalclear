"""Expungement FL router — Phase 17.

Source: phases/source/PHASE_17_expungement_ui.md

Path note: source spec puts this at backend/src/api/routes/expungement.py
and reads disqualifiers via `open("frontend/src/data/...")` from cwd.
The repo's backend/src/api/routes.py is a file (Phase 10 divergence) so
routers live in backend/src/api/routers/. We also resolve the
disqualifiers JSON via __file__ rather than cwd so it works whether
uvicorn starts from repo root (dev) or backend/ (Railway prod).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
from typing import Optional

from src.api.routers.packet import build_packet_with_checkout
from src.services.packet_builder import PacketRequest

router = APIRouter(prefix="/api/expungement")


class EligibilityRequest(BaseModel):
    disposition: str
    charge: str
    completed_terms: str
    previously_sealed: str
    years_since_closed: str
    county: str = "Miami-Dade"
    language: str = "en"
    user_id: Optional[str] = None


# Load disqualifiers once at module load.
# Data file lives in backend/src/data/ (co-located with other JSON data).
_DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "fl_disqualifying_offenses.json"
)
with open(_DATA_FILE) as f:
    DISQUALIFIERS = [d.lower() for d in json.load(f)]


@router.post("/eligibility")
async def check_eligibility(req: EligibilityRequest):
    # TODO: replace with real Claude-generated output (call Phase 07 expungement agent in v1.1)
    charge_lower = req.charge.lower()

    # Hard disqualifiers per §943.0584
    if any(d in charge_lower for d in DISQUALIFIERS):
        return {
            "status": "not_eligible",
            "reason": f"Charges involving '{req.charge}' are disqualifying under FL §943.0584.",
            "applicable_statute": "FL §943.0584",
            "next_steps": [
                "Consult a licensed Florida attorney about case-specific options."
            ],
        }

    if req.previously_sealed == "Yes":
        return {
            "status": "not_eligible",
            "reason": "Florida allows only one expungement or sealing per lifetime.",
            "applicable_statute": "FL §943.0585(2)(b)",
            "next_steps": [
                "No further administrative action is available under FL law.",
                "Consult an attorney about restoration-of-rights alternatives.",
            ],
        }

    if req.disposition == "Adjudicated guilty":
        return {
            "status": "likely_eligible",
            "reason": "Adjudication of guilt generally bars expunction. Sealing may be possible.",
            "applicable_statute": "FL §943.059",
            "next_steps": [
                "Apply for Certificate of Eligibility (FDLE)",
                "Confirm sealing-vs-expunction with a licensed FL attorney",
            ],
        }

    return {
        "status": "eligible",
        "reason": "Based on your answers, you appear eligible to apply for expungement.",
        "applicable_statute": "FL §943.0585",
        "next_steps": [
            "Apply for Certificate of Eligibility from FDLE",
            "File petition in court of original jurisdiction",
            "Pay applicable filing fees",
        ],
    }


@router.post("/generate")
async def generate_expungement_packet(req: EligibilityRequest):
    try:
        return await build_packet_with_checkout(
            PacketRequest(
                packet_type="expungement",
                language=req.language if req.language in ("en", "es") else "en",
                county=req.county,
                user_id=req.user_id or "anon",
                tile_data=req.model_dump(exclude={"language", "user_id"}),
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Packet build failed: {exc}"
        )
