"""California Automated Decision-Making Technology projection.

California Privacy Rights Act (CPRA) automated decision-making provisions.
Implementing regulations: Cal. Code Regs. tit. 11, §§ 7020–7029 (effective Nov 2024).
Underlying statute: Cal. Civ. Code §§ 1798.100 et seq. (as amended by CPRA, Prop 24 2020).

Applies to businesses meeting CPRA thresholds that use ADMT—including profiling,
classification, or significant-decision tools—on California residents.

Key regulations:
  § 7020    — definitions (ADMT, significant decision, profiling)
  § 7021    — general rules; scope of ADMT obligations
  § 7022    — pre-use notice: who, what, why, how ADMT is used
  § 7023    — right to opt out of ADMT in significant decisions
  § 7024    — human review of ADMT-produced significant decisions
  § 7025    — right to opt out of profiling
  § 7026    — training data documentation requirements
  § 7027    — annual audit of ADMT systems; fairness and bias assessment
  § 7028    — risk assessment for certain ADMT uses
  § 7029    — cybersecurity audit

Key statute sections:
  Cal. Civ. Code § 1798.100  — consumer right to access
  Cal. Civ. Code § 1798.121  — sensitive personal information
  Cal. Civ. Code § 1798.150  — private right of action for security breaches

auto_satisfied_by_eu: EU AI Act imposes equivalent or stricter obligations
on transparency, human oversight, data governance, and accuracy.
"""
from __future__ import annotations

from compliance.jurisdictions.base import ProjectionBase
from compliance.schemas.control import Control


class CaliforniaADMTProjection(ProjectionBase):

    @property
    def jurisdiction_key(self) -> str:
        return "california_admt"

    @property
    def jurisdiction_name(self) -> str:
        return (
            "California ADMT (Cal. Code Regs. tit. 11, §§ 7020–7029; "
            "Cal. Civ. Code §§ 1798.100 et seq.)"
        )

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.california_admt)
