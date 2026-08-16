"""Unit tests for the deterministic deadline computation engine — Phase 4.

These tests are pure Python: no LLM calls, no DB calls.
The court_closures table is simulated by passing a frozenset of dates.

Run: cd backend && uv run python -m pytest tests/test_deadline_compute.py -v
"""

from datetime import date, timedelta

import pytest

# Add backend to path so we can import deadline package
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadline.compute import compute_deadline_for_event
from deadline.rules import (
    SERVICE_ESERVICE,
    SERVICE_MAIL,
    SERVICE_PERSONAL,
    SERVICE_POSTED,
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


# ── Statewide holiday calendar (any year, generated in code) ──────────────────

def test_statewide_holidays_2026_match_seeded_closures():
    """Generated 2026 calendar must equal the 9 dates seeded in court_closures
    (20260519220500_phase_3_seed_2026_closures.sql) — keeps evals stable."""
    from deadline.rules import florida_statewide_holidays
    assert florida_statewide_holidays(2026) == frozenset({
        date(2026, 1, 1),    # New Year's Day
        date(2026, 1, 19),   # MLK Day (3rd Monday)
        date(2026, 5, 25),   # Memorial Day (last Monday)
        date(2026, 7, 3),    # Independence Day observed (Jul 4 = Saturday)
        date(2026, 9, 7),    # Labor Day (1st Monday)
        date(2026, 11, 11),  # Veterans Day
        date(2026, 11, 26),  # Thanksgiving (4th Thursday)
        date(2026, 11, 27),  # Day after Thanksgiving
        date(2026, 12, 25),  # Christmas
    })


def test_statewide_holidays_observance_rules():
    """§ 110.117(2): Saturday holiday → preceding Friday; Sunday → following Monday."""
    from deadline.rules import florida_statewide_holidays
    h2027 = florida_statewide_holidays(2027)
    assert date(2027, 7, 5) in h2027 and date(2027, 7, 4) not in h2027    # Jul 4 2027 = Sun → Mon
    assert date(2027, 12, 24) in h2027 and date(2027, 12, 25) not in h2027  # Dec 25 2027 = Sat → Fri
    assert date(2027, 1, 1) in h2027                                       # Jan 1 2027 = Fri, as-is


def test_holiday_roll_forward_2025_no_closures_passed():
    """A 2025 due date landing on July 4 must roll forward even when the caller
    passes NO closure dates (pre-fix, only seeded-2026 rows were honored).

    notice_of_appeal: event Jun 4 2025 (Wed) → +30 = Jul 4 2025 (Fri, holiday)
    → Jul 5 (Sat) → Jul 6 (Sun) → Jul 7 (Mon).
    """
    d = _deadline("notice_of_appeal", date(2025, 6, 4), SERVICE_PERSONAL,
                  today=date(2025, 6, 4))
    assert d.due_date == date(2025, 7, 7)


def test_holiday_roll_forward_across_year_boundary_2027():
    """Event in Dec 2026, due date on New Year's Day 2027 — the year+1 union
    must catch it. civil_summons: Dec 12 2026 + 20 = Jan 1 2027 (Fri, holiday)
    → Jan 2 (Sat) → Jan 3 (Sun) → Jan 4 2027 (Mon)."""
    d = _deadline("civil_summons", date(2026, 12, 12), SERVICE_PERSONAL,
                  today=date(2026, 12, 12))
    assert d.due_date == date(2027, 1, 4)


def test_floating_holiday_mlk_2027():
    """MLK 2027 = Jan 18 (3rd Monday). civil_summons: Dec 29 2026 + 20 =
    Jan 18 2027 (Mon, MLK) → Jan 19 2027 (Tue)."""
    d = _deadline("civil_summons", date(2026, 12, 29), SERVICE_PERSONAL,
                  today=date(2026, 12, 29))
    assert d.due_date == date(2027, 1, 19)


# ── Missing local closure data guardrail (fatal court deadlines) ─────────────

def test_fatal_without_local_closure_data_escalates():
    """Fatal court deadline + no local closure data for the circuit → escalate,
    with a disclosure. Statewide holidays alone are not local data."""
    r = compute_deadline_for_event(
        "civil_summons", ANCHOR, SERVICE_PERSONAL,
        circuit=19, closure_dates=NO_CLOSURES,
        has_local_closure_data=False, today=TODAY,
    )
    d = r.deadlines[0]
    assert d.escalation_recommended is True
    assert r.escalation_needed is True
    assert any("closure" in disc.lower() for disc in d.assumption_disclosures)


def test_fatal_with_local_closure_data_no_escalation():
    """Same fatal deadline WITH local closure data → no escalation."""
    r = compute_deadline_for_event(
        "civil_summons", ANCHOR, SERVICE_PERSONAL,
        circuit=19, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
    )
    assert r.deadlines[0].escalation_recommended is False


def test_non_fatal_without_local_closure_data_no_escalation():
    """Medium-severity deadline without local closure data does NOT escalate."""
    r = compute_deadline_for_event(
        "discovery_request", ANCHOR, SERVICE_PERSONAL,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=False, today=TODAY,
    )
    assert r.deadlines[0].escalation_recommended is False


def test_statutory_sol_ignores_missing_closure_data():
    """SOL/anniversary deadlines never consult the closure calendar, so the
    missing-local-closure-data guardrail must not fire for them."""
    r = compute_deadline_for_event(
        "pc_file_suit", ANCHOR, SERVICE_PERSONAL,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=False, today=TODAY,
    )
    d = r.deadlines[0]
    assert d.escalation_recommended is False
    assert not any("closure" in disc.lower() for disc in d.assumption_disclosures)


# ── Posted service — § 48.183 / Decision 6 ────────────────────────────────
# Effective date is the LATER of the posting date and the clerk's
# certificate-of-mailing date. Missing mailing date → escalate, never compute
# from the posting date alone.

def test_posted_service_computes_from_later_mailing_date_not_posting_date():
    """Posting date X, clerk-mailing date Y (Y > X) → computes from Y."""
    posting_date = ANCHOR                       # 2026-04-01
    mailing_date = ANCHOR + timedelta(days=6)    # 2026-04-07, later than posting

    r = compute_deadline_for_event(
        "civil_summons", posting_date, SERVICE_POSTED,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
        clerk_mailing_date=mailing_date,
    )
    assert r.escalation_needed is False
    assert len(r.deadlines) == 1

    from_mailing = compute_deadline_for_event(
        "civil_summons", mailing_date, SERVICE_PERSONAL,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
    ).deadlines[0].due_date
    from_posting_only = compute_deadline_for_event(
        "civil_summons", posting_date, SERVICE_PERSONAL,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
    ).deadlines[0].due_date

    assert r.deadlines[0].due_date == from_mailing
    assert r.deadlines[0].due_date != from_posting_only
    assert any(
        "later of" in disc.lower() for disc in r.deadlines[0].assumption_disclosures
    )


def test_posted_service_missing_mailing_date_escalates_with_zero_deadlines():
    """No clerk-mailing date supplied → escalate; do NOT compute from posting
    date alone, and do NOT fall through to the earlier-of personal/mail path
    used for unknown/publication service."""
    r = compute_deadline_for_event(
        "civil_summons", ANCHOR, SERVICE_POSTED,
        circuit=None, closure_dates=NO_CLOSURES,
        has_local_closure_data=True, today=TODAY,
        clerk_mailing_date=None,
    )
    assert r.escalation_needed is True
    assert r.deadlines == []
    assert any(
        "certificate-of-mailing" in reason for reason in r.escalation_reasons
    )
