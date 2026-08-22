"""I-3c — PA contract cancellation clocks (§ 626.854(7)) and the NFIP
named-not-shipped decision.

Pure Python unit tests. No LLM, no DB, no network.

Run: cd backend && uv run python -m pytest tests/test_pc_i3c.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from deadline.rules import RULES
from src.agents.property_casualty import PropertyCasualtyExplainer


def _compute(loss_date, **kwargs):
    return PropertyCasualtyExplainer._compute_deadlines(None, loss_date, **kwargs)


def _by_rule(results, citation):
    return [r for r in results if r["governing_rule"] == citation]


# ══════════════════════════════════════════════════════════════════════
# PA contract cancellation — § 626.854(7) — USER action clock
# ══════════════════════════════════════════════════════════════════════

def test_pa_cancel_literal_weekend_endpoint():
    """Executed 2023-03-30 (Thursday) + 10 calendar days = 2023-04-09, a
    SUNDAY. Statutory literal — no 2.514 roll-forward. The statute says
    '10 days', not '10 days or the next business day'."""
    results = _compute(date(2023, 3, 1), pa_contract_executed_date=date(2023, 3, 30))
    matches = _by_rule(results, "Fla. Stat. § 626.854(7)")
    standard = [m for m in matches if m["label"] == "Cancel Public Adjuster Contract"]
    assert len(standard) == 1
    assert standard[0]["due_date"] == "2023-04-09"  # Sunday — stays Sunday
    assert date.fromisoformat(standard[0]["due_date"]).weekday() == 6


def test_pa_cancel_computes_plain_10_days():
    results = _compute(date(2023, 3, 1), pa_contract_executed_date=date(2023, 4, 1))
    matches = _by_rule(results, "Fla. Stat. § 626.854(7)")
    standard = [m for m in matches if m["label"] == "Cancel Public Adjuster Contract"]
    assert len(standard) == 1
    assert standard[0]["due_date"] == "2023-04-11"


def test_pa_cancel_missing_anchor_skips():
    """Without pa_contract_executed_date neither PA cancellation clock
    appears — B1: skip and escalate, never substitute (the emergency
    variant also needs the execution date for its later-of)."""
    results = _compute(date(2023, 3, 1))
    assert _by_rule(results, "Fla. Stat. § 626.854(7)") == []


def test_pa_cancel_emergency_later_of():
    """Loss 2023-03-01, executed 2023-03-15: later_of(loss+30d=2023-03-31,
    executed+10d=2023-03-25) = 2023-03-31."""
    results = _compute(
        date(2023, 3, 1), pa_contract_executed_date=date(2023, 3, 15),
    )
    matches = _by_rule(results, "Fla. Stat. § 626.854(7)")
    emergency = [m for m in matches if m["label"] == "Cancel PA Contract — State of Emergency"]
    assert len(emergency) == 1
    assert emergency[0]["due_date"] == "2023-03-31"


def test_pa_cancel_declares_statutory_literal_counting():
    for key in ("pc_pa_contract_cancel", "pc_pa_contract_cancel_emergency"):
        assert RULES[key]["counting_regime"] == "statutory"


# ══════════════════════════════════════════════════════════════════════
# NFIP — NAMED, NOT SHIPPED
# ══════════════════════════════════════════════════════════════════════

def test_nfip_named_not_shipped():
    """The NFIP clocks (POL 60d, appeal 60d, suit 1yr) are governed by
    44 C.F.R. §§ 61.13 / 62.20 — federal regulations. The owned citation
    corpus is Florida statutes + court rules; PC_CURATED_CITATIONS holds no
    C.F.R. entries, so those authorities cannot resolve against the owned
    corpus (the I-2 loader doctrine). Per Joe's I-3 rule: named, not
    shipped. This test documents the absence — shipping an NFIP clock
    requires a federal-regulatory corpus extension with its own authority
    gate."""
    assert not any(key.startswith("pc_nfip") for key in RULES)
