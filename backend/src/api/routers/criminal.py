"""Module 2 — Criminal Procedure router.

POST /api/criminal/explain — streaming SSE endpoint.
"""

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.criminal_procedure import CriminalProcedureExplainer

router = APIRouter(prefix="/api/criminal")

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_explainer = CriminalProcedureExplainer()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

VALID_SEVERITIES = ["felony", "misdemeanor", "infraction"]
VALID_STAGES = [
    "arrested",
    "charged",
    "arraigned",
    "pretrial",
    "trial",
    "sentencing",
]


class CriminalExplainRequest(BaseModel):
    charge_type: str = Field(..., min_length=1, max_length=200, description="e.g. petit theft, DUI, battery")
    severity: str = Field(..., pattern="^(felony|misdemeanor|infraction)$")
    current_stage: str = Field(..., pattern="^(arrested|charged|arraigned|pretrial|trial|sentencing)$")
    language: str = Field(default="en", pattern="^(en|es)$")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/explain")
async def explain_criminal(payload: CriminalExplainRequest = Body(...)):
    """Stream a plain-English Florida criminal-procedure explanation via SSE."""

    async def _stream():
        async for chunk in _explainer.explain_stream(
            charge_type=payload.charge_type,
            severity=payload.severity,
            current_stage=payload.current_stage,
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
