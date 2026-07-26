"""Expungement FL router — Phase 17.

Source: phases/source/PHASE_17_expungement_ui.md

Path note: source spec puts this at backend/src/api/routes/expungement.py
and reads disqualifiers via `open("frontend/src/data/...")` from cwd.
The repo's backend/src/api/routes.py is a file (Phase 10 divergence) so
routers live in backend/src/api/routers/. Disqualifiers JSON is also
bundled at backend/src/data/fl_disqualifying_offenses.json so Railway
deploys (rootDirectory=/backend, no `frontend/` in the image) can resolve
it via a backend-relative __file__ path. The frontend copy at
frontend/src/data/ stays in place for client-side use.
"""
import json
import logging
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routers.packet import build_packet_with_checkout
from src.core.upl import apply_disclaimer
from src.services.packet_builder import PacketRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expungement")


class EligibilityRequest(BaseModel):
    disposition: str
    charge: str
    completed_terms: str
    previously_sealed: str
    years_since_closed: str
    county: str = "Miami-Dade"
    language: str = "en"
    user_id: str | None = None


# Load disqualifiers once at module load.
# parents[2] from backend/src/api/routers/expungement.py = backend/src/.
# The JSON is bundled inside the backend tree (and a duplicate copy lives
# under frontend/src/data/ for client-side use); reading from the backend
# copy keeps Railway happy because rootDirectory=/backend strips frontend/.
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
        return apply_disclaimer({
            "status": "not_eligible",
            "reason": f"Charges involving '{req.charge}' are disqualifying under FL §943.0584.",
            "applicable_statute": "FL §943.0584",
            "next_steps": [
                "Consult a licensed Florida attorney about case-specific options."
            ],
        }, lang=req.language)

    if req.previously_sealed == "Yes":
        return apply_disclaimer({
            "status": "not_eligible",
            "reason": "Florida allows only one expungement or sealing per lifetime.",
            "applicable_statute": "FL §943.0585(2)(b)",
            "next_steps": [
                "No further administrative action is available under FL law.",
                "Consult an attorney about restoration-of-rights alternatives.",
            ],
        }, lang=req.language)

    if req.disposition == "Adjudicated guilty":
        return apply_disclaimer({
            "status": "likely_eligible",
            "reason": "Adjudication of guilt generally bars expunction. Sealing may be possible.",
            "applicable_statute": "FL §943.059",
            "next_steps": [
                "Apply for Certificate of Eligibility (FDLE)",
                "Confirm sealing-vs-expunction with a licensed FL attorney",
            ],
        }, lang=req.language)

    return apply_disclaimer({
        "status": "eligible",
        "reason": "Based on your answers, you appear eligible to apply for expungement.",
        "applicable_statute": "FL §943.0585",
        "next_steps": [
            "Apply for Certificate of Eligibility from FDLE",
            "File petition in court of original jurisdiction",
            "Pay applicable filing fees",
        ],
    }, lang=req.language)


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
        logger.error(
            "Expungement packet build failed:\n%s",
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500, detail=f"Packet build failed: {exc}"
        ) from exc
