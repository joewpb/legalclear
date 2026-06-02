"""EU AI Act projection — Regulation (EU) 2024/1689, OJ L 2024/1689.

This is the strictest jurisdiction and the primary compliance baseline.
All controls in this projection appear with auto_satisfied_by_eu=False
(EU AI Act is not weaker than itself). EU-compliance status for each
control is determined by the evidence_requirements being satisfied.

Key articles:
  Article 6 + Annex III  — high-risk AI system classification
  Articles 9–15          — high-risk AI system obligations
  Articles 16, 17, 26   — provider and deployer obligations
  Article 50             — transparency for AI interactions
  Article 72             — post-market monitoring
"""
from __future__ import annotations

from compliance.jurisdictions.base import ProjectedControl, ProjectionBase, ProjectionResult
from compliance.schemas.control import Control, Registry


class EUAIActProjection(ProjectionBase):
    """Projects the registry into the EU AI Act compliance view.

    EU AI Act is the strictest baseline. All controls with eu_ai_act
    references are included. auto_satisfied_by_eu is always False here
    because EU AI Act does not satisfy itself — it defines the requirements.
    """

    @property
    def jurisdiction_key(self) -> str:
        return "eu_ai_act"

    @property
    def jurisdiction_name(self) -> str:
        return "EU AI Act (Regulation (EU) 2024/1689)"

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.eu_ai_act)

    def project(self, registry: Registry) -> ProjectionResult:
        projected: list[ProjectedControl] = []

        for ctrl in registry.controls:
            if not self.applies_to(ctrl):
                continue
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
                    applicable_references=ctrl.jurisdiction_mappings.eu_ai_act,
                    eu_ai_act_references=ctrl.jurisdiction_mappings.eu_ai_act,
                    auto_satisfied_by_eu=False,
                )
            )

        return ProjectionResult(
            jurisdiction_key=self.jurisdiction_key,
            jurisdiction_name=self.jurisdiction_name,
            total_controls=len(registry.controls),
            applicable_controls=projected,
            auto_satisfied_count=0,
            independent_verification_count=len(projected),
        )
