"""Florida Digital Bill of Rights projection — Fla. Stat. §§ 501.171–501.1735.

Florida SB 262 (2023), effective July 1, 2023.
§ 501.1735 (children's provisions) effective July 1, 2024.

LegalClear is subject to FDBR as a controller processing personal data of
Florida residents in connection with legal-information services.

Mandatory FDBR coverage areas for LegalClear:

PROFILING (§ 501.1717(1)(c)):
  Consumers have the right to opt out of processing of their personal data for
  profiling in furtherance of decisions that produce legal or similarly
  significant effects. LegalClear's document classification, risk rating,
  and escalation routing qualify as profiling for significant decisions.

AUTOMATED DECISIONS (§ 501.1716(1)(e)):
  Consumers have the right to know when automated processing is used to make
  decisions that produce legal or similarly significant effects, and the right
  to meaningful information about the logic involved.

SENSITIVE DATA (§ 501.1718):
  Legal documents commonly contain sensitive personal data (health, financial,
  criminal record). Processing requires opt-in consent where sensitive
  categories are identified.

CHILDREN (§ 501.1735):
  Data of known minors under 18 must not be processed for profiling or
  targeted advertising. LegalClear's minor-child escalation gate implements
  this requirement by blocking automated processing when children are identified.

SECURITY (§ 501.171):
  Controllers implement and maintain reasonable security procedures and practices.

DATA PROTECTION ASSESSMENT (§ 501.1719):
  Controllers conducting processing that presents heightened risk must complete
  a data protection assessment. Legal-AI tools qualify due to consequential outputs.

auto_satisfied_by_eu: EU AI Act imposes stricter obligations on all dimensions
covered by FDBR. Evidence demonstrating EU AI Act compliance satisfies FDBR
for any control mapped to both frameworks. FDBR-only controls (e.g., §501.1735
children's specific provisions) require independent Florida verification.
"""
from __future__ import annotations

from compliance.jurisdictions.base import ProjectionBase, ProjectedControl, ProjectionResult
from compliance.schemas.control import Control, Registry

# Controls where §501.1735 (children) is the primary or sole FDBR basis.
# These have no direct EU AI Act equivalent and require independent FL verification.
_CHILDREN_FDBR_CONTROLS = {"CTRL-004"}


class FloridaFDBRProjection(ProjectionBase):

    @property
    def jurisdiction_key(self) -> str:
        return "florida_fdbr"

    @property
    def jurisdiction_name(self) -> str:
        return (
            "Florida Digital Bill of Rights (Fla. Stat. §§ 501.171–501.1735, "
            "SB 262 (2023))"
        )

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.florida_fdbr)

    def project(self, registry: Registry) -> ProjectionResult:
        projected: list[ProjectedControl] = []

        for ctrl in registry.controls:
            if not self.applies_to(ctrl):
                continue

            eu_refs = ctrl.jurisdiction_mappings.eu_ai_act
            local_refs = ctrl.jurisdiction_mappings.florida_fdbr

            # Controls grounded primarily in §501.1735 children's provisions
            # have no direct EU AI Act equivalent and require independent FL
            # verification even when EU AI Act compliance is established.
            if ctrl.control_id in _CHILDREN_FDBR_CONTROLS:
                auto_satisfied = False
            else:
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
