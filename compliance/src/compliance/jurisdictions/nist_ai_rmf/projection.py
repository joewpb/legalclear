"""NIST AI Risk Management Framework projection — NIST AI 100-1 (January 2023).

The NIST AI RMF is a voluntary framework, not a jurisdiction with legal force.
It is included as a control-mapping reference and organizational governance baseline.
Controls that satisfy EU AI Act obligations also satisfy corresponding NIST functions.

NIST AI RMF structure:
  GOVERN (GV)  — organizational accountability
  MAP    (MP)  — context and risk identification
  MEASURE (ME) — risk analysis and measurement
  MANAGE (MG)  — risk response and monitoring
"""
from __future__ import annotations

from compliance.jurisdictions.base import ProjectionBase
from compliance.schemas.control import Control


class NISTAIRMFProjection(ProjectionBase):
    """Projects the registry into the NIST AI RMF framework view."""

    @property
    def jurisdiction_key(self) -> str:
        return "nist_ai_rmf"

    @property
    def jurisdiction_name(self) -> str:
        return "NIST AI Risk Management Framework (NIST AI 100-1, January 2023)"

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.nist_ai_rmf)
