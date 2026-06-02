"""Tests: registry.yaml validates against Pydantic schema with zero errors.

Coverage:
  - Registry loads without exception
  - All control_ids match CTRL-NNN format
  - No duplicate control_ids
  - High-risk controls have eu_ai_act mappings
  - All evidence_requirements non-empty
  - All categories are valid
  - version is semver
  - All 9 categories present in the seed registry
"""
from __future__ import annotations

import re

import pytest

from compliance.schemas.control import (
    Control,
    Registry,
    reload_registry,
)

_CTRL_ID_RE = re.compile(r"^CTRL-\d{3}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

VALID_CATEGORIES = {
    "data_governance",
    "transparency",
    "human_oversight",
    "risk_management",
    "technical_robustness",
    "record_keeping",
    "accuracy_bias",
    "security",
    "incident_response",
}


@pytest.fixture(scope="module")
def registry() -> Registry:
    return reload_registry()


def test_registry_loads(registry: Registry) -> None:
    """Registry file exists and parses without exception."""
    assert isinstance(registry, Registry)


def test_registry_version_semver(registry: Registry) -> None:
    assert _SEMVER_RE.match(registry.version), (
        f"version {registry.version!r} is not semver"
    )


def test_registry_has_controls(registry: Registry) -> None:
    assert len(registry.controls) >= 40, (
        f"Expected >= 40 controls, got {len(registry.controls)}"
    )


def test_control_ids_unique(registry: Registry) -> None:
    seen: set[str] = set()
    for ctrl in registry.controls:
        assert ctrl.control_id not in seen, f"Duplicate: {ctrl.control_id}"
        seen.add(ctrl.control_id)


def test_control_ids_format(registry: Registry) -> None:
    bad = [c.control_id for c in registry.controls if not _CTRL_ID_RE.match(c.control_id)]
    assert not bad, f"control_ids with bad format: {bad}"


def test_high_risk_controls_have_eu_mapping(registry: Registry) -> None:
    """Every high-risk control must cite at least one EU AI Act article."""
    failures = [
        c.control_id
        for c in registry.controls
        if c.risk_tier == "high" and not c.jurisdiction_mappings.eu_ai_act
    ]
    assert not failures, (
        f"High-risk controls missing eu_ai_act mappings: {failures}"
    )


def test_evidence_requirements_nonempty(registry: Registry) -> None:
    failures = [
        c.control_id for c in registry.controls if not c.evidence_requirements
    ]
    assert not failures, f"Controls missing evidence_requirements: {failures}"


def test_all_categories_valid(registry: Registry) -> None:
    bad = [
        c.control_id
        for c in registry.controls
        if c.category not in VALID_CATEGORIES
    ]
    assert not bad, f"Controls with invalid category: {bad}"


def test_all_nine_categories_present(registry: Registry) -> None:
    """Seed registry must cover all 9 control categories."""
    found = {c.category for c in registry.controls}
    missing = VALID_CATEGORIES - found
    assert not missing, f"Missing categories in seed registry: {missing}"


def test_by_id_lookup(registry: Registry) -> None:
    ctrl = registry.by_id("CTRL-001")
    assert ctrl is not None
    assert ctrl.control_id == "CTRL-001"


def test_by_id_missing(registry: Registry) -> None:
    assert registry.by_id("CTRL-999") is None


def test_by_category(registry: Registry) -> None:
    security_ctrls = registry.by_category("security")
    assert len(security_ctrls) >= 1
    assert all(c.category == "security" for c in security_ctrls)


def test_automation_status_values(registry: Registry) -> None:
    valid = {"automated", "semi_automated", "manual"}
    bad = [
        c.control_id
        for c in registry.controls
        if c.automation_status not in valid
    ]
    assert not bad, f"Controls with invalid automation_status: {bad}"


def test_risk_tier_values(registry: Registry) -> None:
    valid = {"high", "limited", "minimal"}
    bad = [
        c.control_id
        for c in registry.controls
        if c.risk_tier not in valid
    ]
    assert not bad, f"Controls with invalid risk_tier: {bad}"


def test_eu_citations_are_primary_source(registry: Registry) -> None:
    """EU AI Act citations must reference article/annex numbers (not secondary text)."""
    for ctrl in registry.controls:
        for ref in ctrl.jurisdiction_mappings.eu_ai_act:
            has_article = "Article" in ref or "Annex" in ref
            assert has_article, (
                f"{ctrl.control_id}: EU AI Act citation lacks Article/Annex reference: {ref!r}"
            )


def test_fdbr_citations_are_primary_source(registry: Registry) -> None:
    """Florida FDBR citations must reference §501.17xx statute numbers."""
    for ctrl in registry.controls:
        for ref in ctrl.jurisdiction_mappings.florida_fdbr:
            has_statute = "§ 501." in ref or "501." in ref
            assert has_statute, (
                f"{ctrl.control_id}: FDBR citation lacks statute number: {ref!r}"
            )
