"""Colorado Consumer Artificial Intelligence Act projection.

Colorado HB 24-1468 (C.R.S. §§ 6-1-1701 to 6-1-1711).
Effective: February 1, 2026.

Applies to developers and deployers of "high-risk artificial intelligence systems"
used in "consequential decisions" affecting "significant life areas" including
legal services. LegalClear is covered as a legal-services AI tool.

Key sections:
  § 6-1-1701  — definitions (high-risk AI, consequential decision, significant life area)
  § 6-1-1703  — developer obligations: disclosure, documentation, bias testing
  § 6-1-1704  — deployer obligations: use policy, impact assessment, consumer disclosure
  § 6-1-1705  — impact assessment requirements (annually and before material change)
  § 6-1-1706  — consumer notice requirements before consequential decisions
  § 6-1-1707  — consumer rights: explanation, correction, appeal, opt-out
  § 6-1-1708  — opportunity to appeal an adverse consequential decision
  § 6-1-1709  — exemptions

auto_satisfied_by_eu: a control with EU AI Act references satisfies the Colorado
CAIA version of that control, because EU AI Act imposes stricter requirements on
all dimensions covered by Colorado CAIA.
"""
from __future__ import annotations

from compliance.jurisdictions.base import ProjectionBase
from compliance.schemas.control import Control


class ColoradoCAIAProjection(ProjectionBase):

    @property
    def jurisdiction_key(self) -> str:
        return "colorado_caia"

    @property
    def jurisdiction_name(self) -> str:
        return "Colorado Consumer AI Act (C.R.S. §§ 6-1-1701–6-1-1711, HB 24-1468)"

    def applies_to(self, control: Control) -> bool:
        return bool(control.jurisdiction_mappings.colorado_caia)
