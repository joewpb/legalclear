"""I-3a — regime-aware clock selection + new-clock authority gate.

Pure Python unit tests. No LLM, no DB, no network.

Run: cd backend && uv run python -m pytest tests/test_pc_i3a.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from deadline.rules import RULES, pc_rule_keys_for_regime
from src.agents.pc_citations import PC_CURATED_CITATIONS
from src.agents.property_casualty import PropertyCasualtyExplainer
from src.core.citation_filter import _base_citation
from src.core.citation_resolver import resolve_citation

_ALL_PC_KEYS = {key for key in RULES if key.startswith("pc_")}


# ══════════════════════════════════════════════════════════════════════
# JOB 1 — regime-aware clock selection mechanism
# ══════════════════════════════════════════════════════════════════════

def test_every_pc_rule_declares_regimes():
    for key in _ALL_PC_KEYS:
        regimes = RULES[key].get("regimes")
        assert regimes is not None, f"{key} does not declare regimes"
        assert isinstance(regimes, tuple) and len(regimes) > 0, (
            f"{key} regimes malformed: {regimes!r}"
        )


def test_unknown_regime_selects_nothing():
    """Regime 'unknown' must never select regime-specific content — it
    escalates instead of guessing (mirrors src.core.claim_regime doctrine)."""
    assert pc_rule_keys_for_regime("unknown") == []


def test_none_regime_selects_every_declared_pc_rule():
    """No resolved regime (e.g. no session) preserves pre-I-3a behavior:
    every declared P&C clock is computed unconditionally."""
    assert set(pc_rule_keys_for_regime(None)) == _ALL_PC_KEYS


def test_pre_and_post_regime_both_select_every_current_clock():
    """Every P&C clock today is declared regime-agnostic (regimes=("pre",
    "post")) — the owned corpus shows no regime-varying day count for any
    of the 7 clocks — so "pre" and "post" currently select the same set.
    This locks in that fact; a future regime-specific clock changes it by
    declaration alone (see pc_rule_keys_for_regime docstring)."""
    assert set(pc_rule_keys_for_regime("pre")) == _ALL_PC_KEYS
    assert set(pc_rule_keys_for_regime("post")) == _ALL_PC_KEYS


def test_regime_selection_is_deterministic_and_pure():
    """Selection must be a pure function of RULES + the regime argument —
    calling it repeatedly must be idempotent."""
    first = pc_rule_keys_for_regime("post")
    second = pc_rule_keys_for_regime("post")
    assert first == second


def test_synthetic_regime_specific_clock_excluded_when_unknown(monkeypatch):
    """Mechanism-level guarantee, exercised against a synthetic pre-only
    clock (not a real rule) so this test does not depend on any current
    clock actually being regime-specific."""
    monkeypatch.setitem(
        RULES, "pc_synthetic_pre_only",
        {**RULES["pc_report_claim"], "regimes": ("pre",)},
    )
    assert "pc_synthetic_pre_only" in pc_rule_keys_for_regime("pre")
    assert "pc_synthetic_pre_only" not in pc_rule_keys_for_regime("post")
    assert "pc_synthetic_pre_only" not in pc_rule_keys_for_regime("unknown")


# ══════════════════════════════════════════════════════════════════════
# JOB 2 / JOB 3 — new-clock authority gate (loader doctrine, I-1/I-2)
# ══════════════════════════════════════════════════════════════════════

def _resolves(governing_rule: str) -> bool:
    """Mirrors the loader doctrine (src.content.loader): resolve the BASE
    citation (subsection suffix stripped by the same rule citation_filter
    uses for prose) against the curated map, exact match, no guessing."""
    return resolve_citation(_base_citation(governing_rule), PC_CURATED_CITATIONS) is not None


def test_all_pc_governing_rules_resolve_against_curated_citations():
    """Every P&C rule's governing_rule — old and new — must resolve against
    PC_CURATED_CITATIONS or fail loudly by name."""
    unresolved = [
        (key, rule["governing_rule"])
        for key, rule in RULES.items()
        if key.startswith("pc_") and not _resolves(rule["governing_rule"])
    ]
    assert unresolved == [], f"Unresolved P&C governing_rule citations: {unresolved}"


def test_pc_acknowledge_claim_citation_resolves_to_627_70131():
    rule = RULES["pc_acknowledge_claim"]
    assert rule["governing_rule"] == "Fla. Stat. § 627.70131(1)(a)"
    resolution = resolve_citation(_base_citation(rule["governing_rule"]), PC_CURATED_CITATIONS)
    assert resolution is not None
    assert resolution.citation == "Fla. Stat. § 627.70131"


def test_pc_estimate_delivery_citation_resolves_to_627_70131():
    rule = RULES["pc_estimate_delivery"]
    assert rule["governing_rule"] == "Fla. Stat. § 627.70131(3)(e)"
    resolution = resolve_citation(_base_citation(rule["governing_rule"]), PC_CURATED_CITATIONS)
    assert resolution is not None
    assert resolution.citation == "Fla. Stat. § 627.70131"


def test_unresolvable_governing_rule_fails_loudly_by_name():
    """Sanity-check the gate actually rejects an uncurated citation, not
    just accepts everything."""
    assert not _resolves("Fla. Stat. § 627.99999")


# ══════════════════════════════════════════════════════════════════════
# JOB 2 — pc_estimate_delivery anchor: skip, never guess from date_of_loss
# ══════════════════════════════════════════════════════════════════════

def _compute(loss_date, regime=None, estimate_generated_date=None):
    # _compute_deadlines does not touch `self` — call unbound, no client/DB.
    return PropertyCasualtyExplainer._compute_deadlines(
        None, loss_date, regime=regime, estimate_generated_date=estimate_generated_date,
    )


def test_estimate_delivery_skipped_without_its_anchor():
    """Missing-anchor case: pc_estimate_delivery must not be computed from
    date_of_loss when no estimate_generated_date has been supplied — it is
    silently absent from the result rather than backed by a wrong anchor."""
    results = _compute(date(2023, 3, 1))
    labels = {r["governing_rule"] for r in results}
    assert "Fla. Stat. § 627.70131(3)(e)" not in labels
    # every other declared P&C clock still computes normally
    assert "Fla. Stat. § 627.70132" in labels  # pc_report_claim / pc_supplemental_claim


def test_estimate_delivery_computes_when_anchor_supplied():
    results = _compute(date(2023, 3, 1), estimate_generated_date=date(2023, 4, 1))
    matches = [r for r in results if r["governing_rule"] == "Fla. Stat. § 627.70131(3)(e)"]
    assert len(matches) == 1
    assert matches[0]["due_date"] == "2023-04-10"  # Apr 8 is a Saturday — rolls to Monday


def test_acknowledge_claim_computes_from_loss_date_like_its_siblings():
    """pc_acknowledge_claim shares pc_pay_or_deny's approximation (loss_date
    stands in for claim-notice date in this simplified flow) — it must be
    present whenever loss_date is supplied, same as the other 6 clocks."""
    results = _compute(date(2023, 3, 1))
    matches = [r for r in results if r["governing_rule"] == "Fla. Stat. § 627.70131(1)(a)"]
    assert len(matches) == 1
    assert matches[0]["due_date"] == "2023-03-08"


def test_compute_deadlines_respects_regime_unknown():
    """regime='unknown' must select nothing at the caller layer too."""
    results = _compute(date(2023, 3, 1), regime="unknown")
    assert results == []
