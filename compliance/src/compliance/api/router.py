"""Compliance REST API router.

Endpoints:
  GET  /compliance/controls                   — all controls in registry
  GET  /compliance/controls/{jurisdiction}    — jurisdiction-projected controls
  POST /compliance/evidence                   — submit an evidence artifact
  GET  /compliance/reports/{jurisdiction}     — generate and return a report

Mount into the backend FastAPI app with:
  from compliance.api.router import router as compliance_router
  app.include_router(compliance_router)
"""
from __future__ import annotations

import base64
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from compliance.evidence.manifest import ManifestGenerator
from compliance.evidence.store import get_storage_backend
from compliance.jurisdictions.base import ProjectionResult
from compliance.reports.generator import ReportGenerator, _load_projection
from compliance.schemas.control import Control, Registry, load_registry

router = APIRouter(prefix="/compliance", tags=["compliance"])

_VALID_JURISDICTIONS = [
    "eu_ai_act",
    "nist_ai_rmf",
    "colorado_caia",
    "california_admt",
    "florida_fdbr",
]


# ── Response models ────────────────────────────────────────────────────────────

class ControlResponse(BaseModel):
    control_id: str
    title: str
    category: str
    risk_tier: str
    automation_status: str
    owner_role: str
    evidence_requirements: list[str]
    jurisdiction_keys: list[str]

    @classmethod
    def from_control(cls, ctrl: Control) -> "ControlResponse":
        jm = ctrl.jurisdiction_mappings
        keys = [
            k for k in ["eu_ai_act", "nist_ai_rmf", "colorado_caia",
                         "california_admt", "florida_fdbr"]
            if jm.references_for(k)
        ]
        return cls(
            control_id=ctrl.control_id,
            title=ctrl.title,
            category=ctrl.category,
            risk_tier=ctrl.risk_tier,
            automation_status=ctrl.automation_status,
            owner_role=ctrl.owner_role,
            evidence_requirements=ctrl.evidence_requirements,
            jurisdiction_keys=keys,
        )


class EvidenceSubmission(BaseModel):
    filename: str
    content_base64: str
    control_ids: list[str]
    description: str = ""


class EvidenceResponse(BaseModel):
    sha256: str
    filename: str
    size_bytes: int
    control_ids: list[str]
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/controls", response_model=list[ControlResponse])
def list_controls(
    category: Optional[str] = Query(None, description="Filter by category"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier"),
) -> list[ControlResponse]:
    """Return all controls in the registry, with optional filters."""
    registry: Registry = load_registry()
    controls = registry.controls
    if category:
        controls = [c for c in controls if c.category == category]
    if risk_tier:
        controls = [c for c in controls if c.risk_tier == risk_tier]
    return [ControlResponse.from_control(c) for c in controls]


@router.get("/controls/{jurisdiction}")
def get_controls_by_jurisdiction(jurisdiction: str) -> dict:
    """Return controls projected for a specific jurisdiction.

    The projection includes applicable references, evidence requirements,
    and the auto_satisfied_by_eu flag for each control.
    """
    if jurisdiction not in _VALID_JURISDICTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown jurisdiction: {jurisdiction!r}. Valid: {_VALID_JURISDICTIONS}",
        )
    registry = load_registry()
    projection = _load_projection(jurisdiction)
    result: ProjectionResult = projection.project(registry)
    return {
        "jurisdiction_key": result.jurisdiction_key,
        "jurisdiction_name": result.jurisdiction_name,
        "registry_version": registry.version,
        "summary": {
            "total_controls": result.total_controls,
            "applicable_controls": result.applicable_count,
            "auto_satisfied_by_eu": result.auto_satisfied_count,
            "independent_verification_required": result.independent_verification_count,
        },
        "controls": [c.to_dict() for c in result.applicable_controls],
    }


@router.post("/evidence", response_model=EvidenceResponse)
def submit_evidence(body: EvidenceSubmission) -> EvidenceResponse:
    """Submit an evidence artifact.

    Content must be base64-encoded. The artifact is stored content-addressed
    (SHA-256 as key). Returns the computed SHA-256 for the audit trail.
    """
    try:
        content = base64.b64decode(body.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="content_base64 is not valid base64")

    registry = load_registry()
    valid_ids = [cid for cid in body.control_ids if registry.by_id(cid) is not None]
    if not valid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"None of the provided control_ids are valid: {body.control_ids}",
        )

    storage = get_storage_backend()
    artifact = storage.put(
        content=content,
        filename=body.filename,
        control_ids=valid_ids,
        description=body.description,
    )

    # Regenerate manifest after submission
    ManifestGenerator(storage=storage).save()

    return EvidenceResponse(
        sha256=artifact.sha256,
        filename=artifact.filename,
        size_bytes=artifact.size_bytes,
        control_ids=artifact.control_ids,
        message=f"Artifact stored. SHA-256: {artifact.sha256}",
    )


@router.get("/reports/{jurisdiction}")
def get_report(
    jurisdiction: str,
    fmt: Literal["markdown", "html"] = Query("markdown", alias="format"),
) -> Response:
    """Generate and return a compliance report for a jurisdiction.

    format: 'markdown' (default) or 'html'. PDF is CLI-only (use `legalclear report --format=pdf`).
    """
    if jurisdiction not in _VALID_JURISDICTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown jurisdiction: {jurisdiction!r}. Valid: {_VALID_JURISDICTIONS}",
        )
    gen = ReportGenerator()
    try:
        content = gen.generate_string(jurisdiction=jurisdiction, fmt=fmt)  # type: ignore[arg-type]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    media_type = "text/html" if fmt == "html" else "text/markdown"
    return Response(content=content, media_type=media_type)
