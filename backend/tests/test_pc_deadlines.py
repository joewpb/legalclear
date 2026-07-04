"""Property & Casualty — deadline regression locks (Phase 6).

Pure Python unit tests. No LLM, no DB.
These reproduce every calendar-unit bug caught during Phase 3-revised.

Run: cd backend && uv run python -m pytest tests/test_pc_deadlines.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

import pytest

from deadline.compute import compute_deadline_for_event

NO_CLOSURES: frozenset = frozenset()
TODAY = date.today()


def _deadline(rule_key, event_date, service="personal"):
    r = compute_deadline_for_event(
        rule_key=rule_key,
        event_date=event_date,
        service_method=service,
        circuit=None,
        closure_dates=NO_CLOSURES,
        has_local_closure_data=True,
        today=TODAY,
    )
    assert r.deadlines, f"No deadlines computed for {rule_key}"
    return r.deadlines[0]


# ══════════════════════════════════════════════════════════════════════
# REGRESSION LOCKS — calendar-period leap-crossing
# ══════════════════════════════════════════════════════════════════════

def test_pc_report_claim_leap_crossing():
    """loss 2023-03-01 → must return 2024-03-01 (anniversary).
    The dead 365-day constant returned 2024-02-29 — this IS the guard."""
    dl = _deadline("pc_report_claim", date(2023, 3, 1))
    assert dl.due_date == date(2024, 3, 1), (
        f"Expected 2024-03-01 (1-year anniversary), got {dl.due_date}. "
        f"365-day drift would return 2024-02-29."
    )
    assert dl.governing_rule == "Fla. Stat. § 627.70132"
    assert dl.severity == "fatal"


def test_pc_file_suit_double_leap():
    """loss 2020-01-01 → must return 2025-01-01 (5-year anniversary).
    1826 returned 2024-12-31 — window has two leap days (2020, 2024)."""
    dl = _deadline("pc_file_suit", date(2020, 1, 1))
    assert dl.due_date == date(2025, 1, 1), (
        f"Expected 2025-01-01 (5-year anniversary), got {dl.due_date}. "
        f"1826-day drift would return 2024-12-31."
    )
    assert dl.governing_rule == "Fla. Stat. § 95.11(2)(e)"
    assert dl.severity == "fatal"


def test_pc_supplemental_18mo():
    """loss 2023-07-15 → 18 months = 2025-01-15."""
    dl = _deadline("pc_supplemental_claim", date(2023, 7, 15))
    assert dl.due_date == date(2025, 1, 15), (
        f"Expected 2025-01-15, got {dl.due_date}"
    )
    assert dl.governing_rule == "Fla. Stat. § 627.70132"
    assert dl.severity == "fatal"


def test_pc_feb29_origin_clamp():
    """loss 2024-02-29 + 1 year → must clamp to 2025-02-28 (non-leap)."""
    dl = _deadline("pc_report_claim", date(2024, 2, 29))
    assert dl.due_date == date(2025, 2, 28), (
        f"Expected 2025-02-28 (Feb 29 clamp in non-leap year), got {dl.due_date}"
    )


def test_pc_leap_to_leap_preserved():
    """loss 2024-02-29 + 4 years = 2028-02-29 (both leap)."""
    dl = _deadline("pc_file_suit", date(2024, 2, 29))
    # 5 years from 2024-02-29 = 2029-02-28 (2029 is not leap)
    assert dl.due_date == date(2029, 2, 28), (
        f"Expected 2029-02-28, got {dl.due_date}"
    )


# ══════════════════════════════════════════════════════════════════════
# DAY-COUNT RULES UNCHANGED — calendar branch must not leak into them
# ══════════════════════════════════════════════════════════════════════

def test_pc_pay_or_deny_still_60_calendar_days():
    """pc_pay_or_deny: 60-day insurer deadline, not a calendar-year period.
    Must still compute 60 calendar days from date of loss."""
    dl = _deadline("pc_pay_or_deny", date(2023, 3, 1))
    # 60 calendar days from March 1. March 1 (event), exclude trigger → start
    # March 2. _add_calendar_days(March 2, 59) = April 30 (Sunday).
    # 2.514 roll-forward → Monday May 1. This is correct for day-count rules.
    assert dl.due_date == date(2023, 5, 1), (
        f"Expected 2023-05-01 (60 calendar days, roll-forward from Sun Apr 30), "
        f"got {dl.due_date}"
    )
    assert dl.governing_rule == "Fla. Stat. § 627.70131(7)(a)"
    assert dl.severity == "high"


def test_pc_notice_of_intent_still_10_business_days():
    """pc_notice_of_intent: 10 business days. Must NOT be affected by
    calendar-period changes."""
    # Monday July 6, 2026 → 10 business days = July 20 (Mon)
    dl = _deadline("pc_notice_of_intent", date(2026, 7, 6))
    # Day 1: Tue Jul 7, 2: Wed 8, 3: Thu 9, 4: Fri 10, (skip weekend)
    # 5: Mon 13, 6: Tue 14, 7: Wed 15, 8: Thu 16, 9: Fri 17, (skip weekend)
    # 10: Mon 20
    assert dl.due_date == date(2026, 7, 20), (
        f"Expected 2026-07-20 (10 business days), got {dl.due_date}"
    )
    assert dl.governing_rule == "Fla. Stat. § 627.70152"
    assert dl.severity == "fatal"


def test_daycount_20day_civil_summons_unchanged():
    """Existing day-count rule must still compute identically."""
    dl = _deadline("civil_summons", date(2026, 4, 1))
    assert dl.due_date == date(2026, 4, 21), (
        f"Day-count regression: expected 2026-04-21, got {dl.due_date}"
    )


# ══════════════════════════════════════════════════════════════════════
# COMPUTATION TRACE INTEGRITY
# ══════════════════════════════════════════════════════════════════════

def test_trace_cites_correct_statute():
    """Calendar-period rule trace must cite the Florida statute, not 2.514."""
    dl = _deadline("pc_report_claim", date(2023, 3, 1))
    rules_in_trace = [s["rule"] for s in dl.computation_trace if s.get("rule")]
    assert any("627.70132" in r for r in rules_in_trace), (
        f"Trace must cite §627.70132; got: {rules_in_trace}"
    )


def test_trace_has_no_weekend_roll_forward_for_statutory():
    """Statutory calendar-period deadlines must NOT apply 2.514 roll-forward.
    The trace must confirm 'no weekend/holiday roll-forward'."""
    dl = _deadline("pc_report_claim", date(2023, 3, 1))
    actions = " ".join(s.get("action", "") for s in dl.computation_trace)
    assert "no weekend" in actions.lower() or "statutory deadline" in actions.lower(), (
        f"Trace must indicate no 2.514 roll-forward. Got: {actions[:200]}"
    )


def test_all_pc_deadlines_have_computation_trace():
    """Every P&C deadline must carry a computation_trace."""
    for rule_key in [
        "pc_report_claim", "pc_supplemental_claim", "pc_file_suit",
        "pc_pay_or_deny", "pc_notice_of_intent",
    ]:
        dl = _deadline(rule_key, date(2023, 3, 1))
        assert dl.computation_trace, f"{rule_key} has no computation_trace"
        assert len(dl.computation_trace) >= 2, (
            f"{rule_key} trace too short: {len(dl.computation_trace)} steps"
        )
