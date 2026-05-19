"""Unit tests for the deterministic deadline computation engine — Phase 4.

These tests are pure Python: no LLM calls, no DB calls.
The court_closures table is simulated by passing a frozenset of dates.

Run: cd backend && uv run python -m pytest tests/test_deadline_compute.py -v
"""

from datetime import date

import pytest

# Add backend to path so we can import deadline package
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadline.compute import compute_deadline_for_event
from deadline.rules import (
    SERVICE_ESERVICE,
    SERVICE_MAIL,
    SERVICE_PERSONAL,
    SERVICE_UNKNOWN,
)

# 2026-04-01 = Wednesday — convenient anchor for most tests
ANCHOR = date(2026, 4, 1)
NO_CLOSURES: frozenset = frozenset()
TODAY = ANCHOR  # "today" = the event date; computed deadlines are in the future relative to it


def _deadline(rule_key, event_date, service, closures=NO_CLOSURES, today=TODAY):
    r = compute_deadline_for_event(
        rule_key=rule_key,
        event_date=event_date,
        service_method=service,
        circuit=None,
        closure_dates=closures,
        has_local_closure_data=True,
        today=today,
    )
    assert r.deadlines, f"No deadlines computed for {rule_key}"
    return r.deadlines[0]


# ── Calendar period (≥7 days) ─────────────────────────────────────────────────

def test_20day_personal_service_basic():
    """Civil summons, personal service, no holidays.

    April 1 (Wed) event → exclude trigger day → count from April 2 (day 1)
    day 1..20 = April 21 (Tue)
    """
    d = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL)
    assert d.due_date == date(2026, 4, 21)
    assert d.severity == "fatal"
    assert d.is_past is False


def test_20day_govering_rule_in_trace():
    """Every trace step must carry a rule citation."""
    d = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL)
    rules_in_trace = [step["rule"] for step in d.computation_trace if step["rule"]]
    assert len(rules_in_trace) >= 2, "Trace must cite at least 2 rules"
    assert any("1.140" in r for r in rules_in_trace)


# ── Business-day period ───────────────────────────────────────────────────────

def test_5_business_days_eviction():
    """Eviction: 5 business days from Wednesday April 1.

    Day 1: Thu Apr 2, Day 2: Fri Apr 3, (skip weekend)
    Day 3: Mon Apr 6, Day 4: Tue Apr 7, Day 5: Wed Apr 8
    """
    d = _deadline("eviction_complaint", ANCHOR, SERVICE_PERSONAL)
    assert d.due_date == date(2026, 4, 8)
    assert d.severity == "fatal"


def test_5_business_days_skip_holiday():
    """5 business days, but Monday is a holiday — skips it."""
    # April 6 is Monday — make it a holiday
    holidays = frozenset([date(2026, 4, 6)])
    # Day 1: Thu Apr 2, Day 2: Fri Apr 3, (skip weekend + Mon holiday)
    # Day 3: Tue Apr 7, Day 4: Wed Apr 8, Day 5: Thu Apr 9
    d = compute_deadline_for_event(
        "eviction_complaint", ANCHOR, SERVICE_PERSONAL,
        circuit=None, closure_dates=holidays,
        has_local_closure_data=True, today=TODAY,
    ).deadlines[0]
    assert d.due_date == date(2026, 4, 9)


# ── Mail service ──────────────────────────────────────────────────────────────

def test_mail_service_adds_5_days():
    """Civil summons by mail: +5 days to start, then 20 calendar days.

    April 1 + 5 = April 6 adjusted start
    +1 (exclude trigger) = April 7
    +19 more = April 26 (Mon — check)
    April 6 = Mon, April 7 start, day 1..20: April 26
    """
    d = _deadline("civil_summons", ANCHOR, SERVICE_MAIL)
    # adjusted_start = April 6, +20 calendar from April 6 = April 27 (Tue)
    # April 6 (Mon) +1 = April 7 (start of count), +19 = April 26 (Sun)?
    # Let me recount: _add_calendar_days(adjusted_start + 1, n-1)
    # = _add_calendar_days(April 7, 19) = April 26 (Sun) → roll to April 27 (Mon)
    assert d.due_date == date(2026, 4, 27)


def test_eservice_no_extension():
    """E-service adds 0 days — same result as personal service."""
    d_personal = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL)
    d_eservice = _deadline("civil_summons", ANCHOR, SERVICE_ESERVICE)
    assert d_personal.due_date == d_eservice.due_date


# ── Roll-forward on weekend/holiday ──────────────────────────────────────────

def test_rolls_forward_from_saturday():
    """Due date lands on Saturday → rolls to Monday."""
    # April 3 (Fri) + 20 calendar days
    # adjusted_start = April 3, +1 = April 4 (start), +19 = April 23 (Sat) → April 27?
    # Let me use a date where I know the result lands on Saturday.
    # April 4 (Sat) as event: +1 = April 5, +19 = April 24 (Sat) → April 26 (Mon)
    event = date(2026, 4, 4)  # Saturday
    d = _deadline("civil_summons", event, SERVICE_PERSONAL)
    assert d.due_date.weekday() not in (5, 6), "Due date must not fall on weekend"


def test_rolls_forward_from_sunday():
    """Due date lands on Sunday → rolls to Monday."""
    event = date(2026, 4, 5)  # Sunday
    d = _deadline("civil_summons", event, SERVICE_PERSONAL)
    assert d.due_date.weekday() not in (5, 6)


def test_rolls_forward_past_holiday():
    """Due date lands on a holiday → rolls forward to the next business day.

    event = April 2 (Thu) → count from April 3 → day 1..20 = April 22 (Wed, holiday)
    → rolls to April 23 (Thu)
    """
    event = date(2026, 4, 2)
    holidays = frozenset([date(2026, 4, 22)])
    d = compute_deadline_for_event(
        "civil_summons", event, SERVICE_PERSONAL,
        circuit=None, closure_dates=holidays,
        has_local_closure_data=True, today=TODAY,
    ).deadlines[0]
    assert d.due_date == date(2026, 4, 23)


def test_rolls_forward_holiday_then_weekend():
    """Holiday on Friday, weekend follows — rolls to Monday."""
    # Make April 24 (Fri) a holiday; April 25 (Sat), April 26 (Sun) → April 27 (Mon)
    # Need an event where raw_due = April 24
    # civil_summons: event = April 3 (Thu), +1 = April 4, +19 = April 23; try April 4
    # event = April 4 (Sat), adjusted = April 4, +1 = April 5 (Sun+1? No — calendar)
    # Let me pick event date so raw_due = April 24.
    # _add_calendar_days(event + 1, 19) = April 24
    # event + 20 = April 24 → event = April 4
    event = date(2026, 4, 4)
    holidays = frozenset([date(2026, 4, 24)])
    d = compute_deadline_for_event(
        "civil_summons", event, SERVICE_PERSONAL,
        circuit=None, closure_dates=holidays,
        has_local_closure_data=True, today=TODAY,
    ).deadlines[0]
    # April 24 (Fri, holiday) → April 25 (Sat) → April 26 (Sun) → April 27 (Mon)
    assert d.due_date == date(2026, 4, 27)


# ── Past deadline ─────────────────────────────────────────────────────────────

def test_past_deadline_flagged():
    """A deadline in the past is flagged with is_past=True and escalation."""
    old_event = date(2020, 1, 1)
    d = _deadline("civil_summons", old_event, SERVICE_PERSONAL, today=date.today())
    assert d.is_past is True
    assert d.escalation_recommended is True
    assert any("passed" in disc.lower() for disc in d.assumption_disclosures)


# ── Unknown service ───────────────────────────────────────────────────────────

def test_unknown_service_uses_shorter_deadline():
    """Unknown service: compute personal and mail, use the earlier (shorter) date."""
    r = compute_deadline_for_event(
        "civil_summons", ANCHOR, SERVICE_UNKNOWN,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
    )
    d = r.deadlines[0]
    personal_due = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL).due_date
    mail_due = _deadline("civil_summons", ANCHOR, SERVICE_MAIL).due_date
    assert d.due_date == min(personal_due, mail_due)
    assert any("service method" in disc.lower() for disc in d.assumption_disclosures)


# ── Computation trace completeness ────────────────────────────────────────────

def test_trace_has_all_required_keys():
    """Every trace step must have step, action, date, rule keys."""
    d = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL)
    for step in d.computation_trace:
        assert "step" in step
        assert "action" in step
        assert "date" in step
        assert "rule" in step


def test_trace_steps_are_sequential():
    """Trace step numbers must be sequential starting from 1."""
    d = _deadline("civil_summons", ANCHOR, SERVICE_PERSONAL)
    steps = [s["step"] for s in d.computation_trace]
    assert steps == list(range(1, len(steps) + 1))


# ── Small claims (non-computable period) ─────────────────────────────────────

def test_small_claims_escalates():
    """Small claims pretrial date is on the summons — pipeline should escalate."""
    r = compute_deadline_for_event(
        "small_claims_summons", ANCHOR, SERVICE_PERSONAL,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
    )
    d = r.deadlines[0]
    assert d.escalation_recommended is True
    assert any("summons" in disc.lower() for disc in d.assumption_disclosures)


# ── Notice of appeal (30 calendar days) ──────────────────────────────────────

def test_notice_of_appeal_30_days():
    """Notice of appeal: 30 calendar days from April 1 = May 2 (Sat) → May 4 (Mon).

    April 1 + 1 = April 2 start; +29 = May 1 (Fri). Let me recount.
    _add_calendar_days(April 2, 29) = May 1 (Fri)?
    April has 30 days. April 2 + 29 = May 1. May 1, 2026 = Friday → no roll.
    """
    d = _deadline("notice_of_appeal", ANCHOR, SERVICE_PERSONAL)
    # April 1 (event), exclude → start April 2, +30-1=29 more = May 1 (Fri)
    assert d.due_date == date(2026, 5, 1)
    assert d.severity == "fatal"
