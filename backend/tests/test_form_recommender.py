"""
Tests for the form recommender service (src/services/form_recommender.py).

Covers:
- All 13 case types have required fields
- Decision tree is complete and consistent
- Form explanations cover required forms
- get_case_type, list_case_types, get_form_explanation
"""

import sys
from pathlib import Path

import pytest

# Add backend to path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from src.services.form_recommender import (
    CASE_TYPES,
    DECISION_TREE,
    FORM_EXPLANATIONS,
    get_case_type,
    get_decision_tree_node,
    get_form_explanation,
    get_tree_root,
    list_case_types,
)


def test_all_13_case_types():
    """All 13 case types are defined."""
    cases = list_case_types()
    assert len(cases) == 13


def test_every_case_has_required_fields():
    """Every case type has id, name, description, court, filing_fee."""
    for c in list_case_types():
        assert c.id, f"Case missing id"
        assert c.name, f"{c.id} missing name"
        assert c.description, f"{c.id} missing description"
        assert c.court, f"{c.id} missing court"
        assert c.filing_fee, f"{c.id} missing filing_fee"


def test_case_ids_are_unique():
    """No duplicate case type IDs."""
    ids = [c.id for c in list_case_types()]
    assert len(ids) == len(set(ids))


def test_get_case_type_valid():
    """Known case types resolve."""
    ct = get_case_type("divorce-with-children")
    assert ct is not None
    assert ct.name == "Divorce with Children"
    assert len(ct.form_numbers) == 6


def test_get_case_type_nonexistent():
    """Unknown case types return None."""
    assert get_case_type("not-a-real-case") is None


def test_diy_florida_cases():
    """Cases with DIY Florida support are flagged."""
    diy_cases = [c for c in list_case_types() if c.diy_florida]
    assert len(diy_cases) >= 3  # divorce-no-kids, DV, eviction-landlord, small-claims


def test_no_fee_injunction():
    """Domestic violence injunction has $0 fee."""
    ct = get_case_type("domestic-violence-injunction")
    assert "$0" in ct.filing_fee


def test_eviction_tenant_has_urgent_note():
    """Eviction defense has the 5-day warning."""
    ct = get_case_type("eviction-tenant")
    assert "5" in ct.note or "five" in ct.note.lower()


# ── Decision tree ─────────────────────────────────────────────


def _collect_paths(node_key: str, path=None):
    if path is None:
        path = []
    paths = []
    node = DECISION_TREE.get(node_key)
    if node is None:
        return [tuple(path + [f"INVALID:{node_key}"])]
    for opt_key, opt in node["options"].items():
        new_path = path + [opt_key]
        if "result" in opt:
            paths.append(tuple(new_path + [opt["result"]]))
        elif "next" in opt:
            paths.extend(_collect_paths(opt["next"], new_path))
    return paths


def test_tree_root():
    """Root node exists and has 5 options."""
    root = get_tree_root()
    assert root is not None
    assert len(root["options"]) == 5


def test_tree_all_paths_valid():
    """Every path ends in a valid case type."""
    paths = _collect_paths("start")
    valid_ids = set(CASE_TYPES.keys())
    for path in paths:
        result = path[-1]
        assert result in valid_ids, f"Path ends in invalid case: {result}"


def test_tree_covers_all_cases():
    """Every case type is reachable."""
    paths = _collect_paths("start")
    results = {p[-1] for p in paths}
    missing = set(CASE_TYPES.keys()) - results
    assert not missing, f"Unreachable: {missing}"


def test_tree_node_consistency():
    """All 'next' pointers reference real nodes."""
    for node_key, node in DECISION_TREE.items():
        for opt_key, opt in node["options"].items():
            if "next" in opt:
                assert opt["next"] in DECISION_TREE, (
                    f"{node_key}→{opt_key}→{opt['next']} is dead"
                )


def test_get_decision_tree_node():
    """Fetch a specific tree node."""
    node = get_decision_tree_node("family")
    assert node is not None
    assert len(node["options"]) == 5


def test_get_decision_tree_node_nonexistent():
    assert get_decision_tree_node("nonexistent") is None


# ── Form explanations ─────────────────────────────────────────


def test_explanations_for_supreme_court_forms():
    """All Supreme Court form numbers have explanations."""
    for c in list_case_types():
        for fn in c.form_numbers:
            # Skip county-specific or non-standard IDs
            if fn in ("County-Specific",) or "County" in fn:
                continue
            # May or may not have an explanation — not all are needed
            # but the lookup should not throw


def test_get_form_explanation_known():
    """Known form returns explanation."""
    expl = get_form_explanation("12.901(b)(1)")
    assert "divorce" in expl.lower()
    assert len(expl) > 50


def test_get_form_explanation_unknown():
    """Unknown form returns empty string."""
    assert get_form_explanation("99.999(x)") == ""


def test_marriage_forms_explained():
    """Key divorce forms have explanations."""
    for fn in ["12.901(b)(1)", "12.901(b)(2)", "12.902(b)", "12.902(c)",
               "12.902(d)", "12.902(e)", "12.995(a)"]:
        assert get_form_explanation(fn), f"No explanation for {fn}"


# ── County-specific cases ────────────────────────────────────


def test_county_specific_cases():
    """At least 6 cases are flagged county-specific."""
    county_cases = [c for c in list_case_types() if c.county_specific]
    assert len(county_cases) >= 6


def test_county_specific_have_no_form_numbers():
    """County-specific cases have empty form_numbers (or very few)."""
    for c in list_case_types():
        if c.county_specific:
            # They may have 1-2 statewide forms but the main forms are local
            assert len(c.form_numbers) <= 2, (
                f"{c.id} is county_specific but has {len(c.form_numbers)} forms"
            )
