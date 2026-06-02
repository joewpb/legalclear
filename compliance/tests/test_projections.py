"""Tests: jurisdiction projection correctness.

Key invariants:
  1. EU AI Act projection: auto_satisfied_by_eu is always False (EU satisfies itself)
  2. Weaker jurisdictions: auto_satisfied_by_eu=True iff control has eu_ai_act refs
  3. Controls with no jurisdiction mapping don't appear in that projection
  4. CTRL-004 (children's data): auto_satisfied_by_eu=False in FL FDBR projection
     because §501.1735 has no direct EU AI Act equivalent
  5. A control that appears in EU projection must have eu_ai_act refs (by definition)
  6. Projection is deterministic: same output for same input
"""
from __future__ import annotations

import pytest

from compliance.jurisdictions.eu_ai_act import EUAIActProjection
from compliance.jurisdictions.nist_ai_rmf import NISTAIRMFProjection
from compliance.jurisdictions.colorado_caia import ColoradoCAIAProjection
from compliance.jurisdictions.california_admt import CaliforniaADMTProjection
from compliance.jurisdictions.florida_fdbr import FloridaFDBRProjection
from compliance.schemas.control import Registry, reload_registry


@pytest.fixture(scope="module")
def registry() -> Registry:
    return reload_registry()


# ── EU AI Act ──────────────────────────────────────────────────────────────────

def test_eu_projection_auto_satisfied_always_false(registry: Registry) -> None:
    result = EUAIActProjection().project(registry)
    bad = [c.control_id for c in result.applicable_controls if c.auto_satisfied_by_eu]
    assert not bad, (
        "EU AI Act projection must never set auto_satisfied_by_eu=True. "
        f"Found: {bad}"
    )


def test_eu_projection_all_controls_have_eu_refs(registry: Registry) -> None:
    result = EUAIActProjection().project(registry)
    for ctrl in result.applicable_controls:
        assert ctrl.eu_ai_act_references, (
            f"{ctrl.control_id} in EU projection but has no eu_ai_act references"
        )
        assert ctrl.applicable_references, (
            f"{ctrl.control_id} in EU projection but applicable_references is empty"
        )


def test_eu_projection_count_equals_registry(registry: Registry) -> None:
    result = EUAIActProjection().project(registry)
    # All 49 seed controls have eu_ai_act mappings (high-risk requirement)
    high_count = sum(1 for c in registry.controls if c.jurisdiction_mappings.eu_ai_act)
    assert result.applicable_count == high_count


def test_eu_projection_auto_count_is_zero(registry: Registry) -> None:
    result = EUAIActProjection().project(registry)
    assert result.auto_satisfied_count == 0
    assert result.independent_verification_count == result.applicable_count


# ── Colorado CAIA ──────────────────────────────────────────────────────────────

def test_colorado_auto_satisfied_when_has_eu_refs(registry: Registry) -> None:
    result = ColoradoCAIAProjection().project(registry)
    for ctrl in result.applicable_controls:
        expected = bool(ctrl.eu_ai_act_references)
        assert ctrl.auto_satisfied_by_eu == expected, (
            f"{ctrl.control_id}: auto_satisfied_by_eu={ctrl.auto_satisfied_by_eu} "
            f"but eu_ai_act_references={'present' if ctrl.eu_ai_act_references else 'empty'}"
        )


def test_colorado_projection_has_controls(registry: Registry) -> None:
    result = ColoradoCAIAProjection().project(registry)
    assert result.applicable_count > 0


def test_colorado_projection_references_colorado_statutes(registry: Registry) -> None:
    result = ColoradoCAIAProjection().project(registry)
    for ctrl in result.applicable_controls:
        for ref in ctrl.applicable_references:
            assert "6-1-17" in ref, (
                f"{ctrl.control_id}: Colorado reference lacks C.R.S. §6-1-17xx: {ref!r}"
            )


# ── California ADMT ────────────────────────────────────────────────────────────

def test_california_auto_satisfied_when_has_eu_refs(registry: Registry) -> None:
    result = CaliforniaADMTProjection().project(registry)
    for ctrl in result.applicable_controls:
        expected = bool(ctrl.eu_ai_act_references)
        assert ctrl.auto_satisfied_by_eu == expected, (
            f"{ctrl.control_id}: auto_satisfied mismatch"
        )


def test_california_projection_has_controls(registry: Registry) -> None:
    result = CaliforniaADMTProjection().project(registry)
    assert result.applicable_count > 0


# ── Florida FDBR ───────────────────────────────────────────────────────────────

def test_fdbr_projection_has_controls(registry: Registry) -> None:
    result = FloridaFDBRProjection().project(registry)
    assert result.applicable_count > 0


def test_fdbr_ctrl004_not_auto_satisfied(registry: Registry) -> None:
    """CTRL-004 (Children's Data) must NOT be auto-satisfied by EU AI Act.

    §501.1735 children's provisions have no direct EU AI Act equivalent.
    The FDBR projection explicitly keeps this as needing independent FL verification.
    """
    result = FloridaFDBRProjection().project(registry)
    ctrl004 = next(
        (c for c in result.applicable_controls if c.control_id == "CTRL-004"), None
    )
    assert ctrl004 is not None, "CTRL-004 should appear in FDBR projection"
    assert ctrl004.auto_satisfied_by_eu is False, (
        "CTRL-004 must NOT be auto_satisfied_by_eu in FDBR — §501.1735 "
        "children's provisions require independent Florida verification"
    )


def test_fdbr_other_controls_auto_satisfied(registry: Registry) -> None:
    """Non-children controls with EU refs should be auto-satisfied in FDBR projection."""
    result = FloridaFDBRProjection().project(registry)
    non_children = [
        c for c in result.applicable_controls
        if c.control_id != "CTRL-004"
    ]
    auto_with_eu = [c for c in non_children if c.eu_ai_act_references]
    not_auto = [c for c in auto_with_eu if not c.auto_satisfied_by_eu]
    assert not not_auto, (
        f"Non-children FDBR controls with EU refs should be auto-satisfied: "
        f"{[c.control_id for c in not_auto]}"
    )


def test_fdbr_references_florida_statutes(registry: Registry) -> None:
    result = FloridaFDBRProjection().project(registry)
    for ctrl in result.applicable_controls:
        for ref in ctrl.applicable_references:
            has_fla_stat = "Fla. Stat." in ref or "501." in ref
            assert has_fla_stat, (
                f"{ctrl.control_id}: FDBR reference missing Fla. Stat. citation: {ref!r}"
            )


# ── NIST AI RMF ───────────────────────────────────────────────────────────────

def test_nist_projection_has_controls(registry: Registry) -> None:
    result = NISTAIRMFProjection().project(registry)
    assert result.applicable_count > 0


def test_nist_references_rmf_functions(registry: Registry) -> None:
    result = NISTAIRMFProjection().project(registry)
    valid_prefixes = ("GOVERN", "MAP", "MEASURE", "MANAGE")
    for ctrl in result.applicable_controls:
        for ref in ctrl.applicable_references:
            assert any(ref.startswith(p) for p in valid_prefixes), (
                f"{ctrl.control_id}: NIST reference doesn't start with a "
                f"valid function: {ref!r}"
            )


# ── Cross-jurisdiction invariants ─────────────────────────────────────────────

def test_eu_strictest_superset(registry: Registry) -> None:
    """EU AI Act projection must be a superset of high-risk controls in each other jurisdiction.

    Any control that is high-risk AND appears in CO/CA/FL must also appear in EU.
    """
    eu_ids = {
        c.control_id
        for c in EUAIActProjection().project(registry).applicable_controls
    }
    for Projection in (ColoradoCAIAProjection, CaliforniaADMTProjection, FloridaFDBRProjection):
        result = Projection().project(registry)  # type: ignore[call-arg]
        for ctrl in result.applicable_controls:
            if ctrl.risk_tier == "high" and ctrl.eu_ai_act_references:
                assert ctrl.control_id in eu_ids, (
                    f"{ctrl.control_id} is high-risk with EU refs but missing "
                    f"from EU projection (projection={Projection.__name__})"
                )


def test_projection_deterministic(registry: Registry) -> None:
    """Two calls with same input must produce identical output."""
    r1 = FloridaFDBRProjection().project(registry)
    r2 = FloridaFDBRProjection().project(registry)
    assert [c.control_id for c in r1.applicable_controls] == [
        c.control_id for c in r2.applicable_controls
    ]
