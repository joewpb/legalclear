"""I-3b — CRN cure window, loss-assessment later-of, and the mediation
named-not-shipped decision.

Pure Python unit tests. No LLM, no DB, no network.

Run: cd backend && uv run python -m pytest tests/test_pc_i3b.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from deadline.compute import compute_deadline_for_event
from deadline.rules import RULES
from src.agents.property_casualty import PropertyCasualtyExplainer


def _compute(loss_date, **kwargs):
    # _compute_deadlines does not touch `self` — call unbound, no client/DB.
    return PropertyCasualtyExplainer._compute_deadlines(None, loss_date, **kwargs)


def _by_rule(results, citation):
    return [r for r in results if r["governing_rule"] == citation]


# ══════════════════════════════════════════════════════════════════════
# CRN — pc_crn_cure (§ 624.155(3)(a)) — USER action clock
# ══════════════════════════════════════════════════════════════════════

def test_crn_missing_anchor_skips():
    """Without crn_filed_date the CRN clock must not appear — B1: skip and
    escalate, never substitute date_of_loss for the CRN filing date."""
    results = _compute(date(2023, 3, 1))
    assert _by_rule(results, "Fla. Stat. § 624.155(3)(a)") == []


def test_crn_literal_weekend_endpoint():
    """Joe's explicit requirement: the CRN 60-day cure window must equal the
    LITERAL calendar date even when it lands on a weekend. 2023-01-03 is a
    Tuesday; +60 calendar days = 2023-03-04, a SATURDAY. No 2.514
    roll-forward — a rolled endpoint here is a cure window someone misses."""
    results = _compute(date(2023, 1, 1), crn_filed_date=date(2023, 1, 3))
    matches = _by_rule(results, "Fla. Stat. § 624.155(3)(a)")
    assert len(matches) == 1
    assert matches[0]["due_date"] == "2023-03-04"  # Saturday — stays Saturday
    assert date.fromisoformat(matches[0]["due_date"]).weekday() == 5


def test_crn_declares_statutory_literal_counting():
    rule = RULES["pc_crn_cure"]
    assert rule["counting_regime"] == "statutory"
    assert rule["day_counting"] == "calendar"
    assert not rule["explicitly_business_days"]


# ══════════════════════════════════════════════════════════════════════
# Loss assessment — pc_loss_assessment (§ 627.70132(4)(a)) — later-of
# ══════════════════════════════════════════════════════════════════════

def test_loss_assessment_happy_path():
    """Loss 2023-03-01, vote 2023-06-01: later_of(2024-03-01, 2023-08-30) =
    2024-03-01, within the 3-year outer bound (2026-03-01)."""
    results = _compute(date(2023, 3, 1), association_vote_date=date(2023, 6, 1))
    matches = _by_rule(results, "Fla. Stat. § 627.70132(4)(a)")
    assert len(matches) == 1
    assert matches[0]["due_date"] == "2024-03-01"


def test_loss_assessment_late_vote_wins_later_of():
    """A late vote extends the deadline: vote 2025-01-01 → candidate
    2025-04-01 beats loss+1yr (2024-03-01); still inside the 2026-03-01
    outer bound."""
    results = _compute(date(2023, 3, 1), association_vote_date=date(2025, 1, 1))
    matches = _by_rule(results, "Fla. Stat. § 627.70132(4)(a)")
    assert len(matches) == 1
    assert matches[0]["due_date"] == "2025-04-01"


def test_loss_assessment_missing_vote_skips():
    """Without the association vote date the later-of cannot be computed —
    the clock is skipped, never computed from date_of_loss alone (B1)."""
    results = _compute(date(2023, 3, 1))
    assert _by_rule(results, "Fla. Stat. § 627.70132(4)(a)") == []


def test_loss_assessment_barred_escalates_no_date():
    """Vote 2026-06-01 → later-of candidate 2026-08-30 exceeds the 3-year
    outer bound (2026-03-01): the claim is barred — escalate, emit NO date."""
    result = compute_deadline_for_event(
        rule_key="pc_loss_assessment",
        event_date=date(2023, 3, 1),
        service_method="personal",
        circuit=None,
        closure_dates=frozenset(),
        has_local_closure_data=True,
        today=date(2023, 3, 1),
        extra_dates={"association_vote": date(2026, 6, 1)},
    )
    assert result.deadlines == []
    assert result.escalation_needed is True
    assert any("barred" in r for r in result.escalation_reasons)


def test_loss_assessment_literal_no_roll():
    """Later-of candidates use literal statutory arithmetic — no 2.514
    roll. Loss 2023-04-01 (Sat) + 1yr = 2024-04-01 (Monday), fine; assert
    the counting regime declaration instead of a date for this case."""
    rule = RULES["pc_loss_assessment"]
    assert rule["counting_regime"] == "statutory"


# ══════════════════════════════════════════════════════════════════════
# Mediation 21-day — NAMED, NOT SHIPPED (Joe's rule: authority that does
# not resolve does not ship)
# ══════════════════════════════════════════════════════════════════════

def test_mediation_21d_named_not_shipped():
    """The owned § 627.7015 text (current, post-reform) contains NO 21-day
    mediation window — the pre-reform 21-day timeline is not in the corpus,
    and the current text's only day-counted provision is the 3-business-day
    rescission window in § 627.7015(6)(a). Per Joe's I-3 rule, a clock whose
    day count does not resolve against the owned text does not ship; it is
    named instead. This test documents the absence — if a future corpus
    refresh adds the 21-day window, adding the clock becomes a deliberate
    act with its own authority gate."""
    assert "pc_mediation_window" not in RULES
