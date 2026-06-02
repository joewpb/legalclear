"""Abstract base class for jurisdiction projections.

Design invariant (from Phase 1 spec):
  A control that satisfies the EU AI Act automatically satisfies all weaker
  jurisdictions it also maps to. This is implemented deterministically:
  if a control has eu_ai_act references AND references for a weaker jurisdiction,
  the projected control for that weaker jurisdiction carries auto_satisfied_by_eu=True.
  Evidence demonstrating EU AI Act compliance is sufficient for those references.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from compliance.schemas.control import Control, Registry


class ProjectedControl(BaseModel):
    control_id: str
    title: str
    description: str
    category: str
    risk_tier: str
    automation_status: str
    owner_role: str
    evidence_requirements: list[str]
    applicable_references: list[str]
    eu_ai_act_references: list[str]
    # True when the control also has EU AI Act references — EU compliance
    # is sufficient to satisfy this jurisdiction's version of the control.
    auto_satisfied_by_eu: bool

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ProjectionResult(BaseModel):
    jurisdiction_key: str
    jurisdiction_name: str
    total_controls: int
    applicable_controls: list[ProjectedControl]
    auto_satisfied_count: int
    independent_verification_count: int

    @property
    def applicable_count(self) -> int:
        return len(self.applicable_controls)

    def by_category(self) -> dict[str, list[ProjectedControl]]:
        result: dict[str, list[ProjectedControl]] = {}
        for ctrl in self.applicable_controls:
            result.setdefault(ctrl.category, []).append(ctrl)
        return result


class ProjectionBase(ABC):
    """Base class for a jurisdiction projection.

    Subclasses implement:
    - jurisdiction_key: matches the field name in JurisdictionMappings
    - jurisdiction_name: human-readable name for reports
    - applies_to(control): True if this control has references for this jurisdiction
    """

    @property
    @abstractmethod
    def jurisdiction_key(self) -> str: ...

    @property
    @abstractmethod
    def jurisdiction_name(self) -> str: ...

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.references_for(self.jurisdiction_key))

    def project(self, registry: Registry) -> ProjectionResult:
        projected: list[ProjectedControl] = []

        for ctrl in registry.controls:
            if not self.applies_to(ctrl):
                continue

            eu_refs = ctrl.jurisdiction_mappings.eu_ai_act
            local_refs = ctrl.jurisdiction_mappings.references_for(self.jurisdiction_key)
            auto_satisfied = bool(eu_refs)

            projected.append(
                ProjectedControl(
                    control_id=ctrl.control_id,
                    title=ctrl.title,
                    description=ctrl.description,
                    category=ctrl.category,
                    risk_tier=ctrl.risk_tier,
                    automation_status=ctrl.automation_status,
                    owner_role=ctrl.owner_role,
                    evidence_requirements=ctrl.evidence_requirements,
                    applicable_references=local_refs,
                    eu_ai_act_references=eu_refs,
                    auto_satisfied_by_eu=auto_satisfied,
                )
            )

        auto_count = sum(1 for p in projected if p.auto_satisfied_by_eu)
        return ProjectionResult(
            jurisdiction_key=self.jurisdiction_key,
            jurisdiction_name=self.jurisdiction_name,
            total_controls=len(registry.controls),
            applicable_controls=projected,
            auto_satisfied_count=auto_count,
            independent_verification_count=len(projected) - auto_count,
        )
