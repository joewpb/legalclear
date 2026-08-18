"""Decision 6 worked examples — § 48.183 service-method timing equivalence.

Pure Python, no LLM, no DB. Locks the three dates confirmed by the
four-case live gate (2026-08-17 night run) and re-confirmed by the legal
answer on § 48.183(2) received 2026-08-18 (see DECISIONS.md Decision 6).

Run: cd backend && uv run python -m pytest tests/test_decision6_worked_examples.py -v
"""

from datetime import date

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadline.compute import compute_deadline_for_event


def _due(method: str, event: date, mailing: date | None = None) -> date:
    res = compute_deadline_for_event(
        rule_key="eviction_complaint",          # 5 business days, explicitly_business_days=True
        event_date=event,
        service_method=method,
        circuit=None,
        closure_dates=frozenset(),              # no local closures; statewide holidays apply
        has_local_closure_data=True,
        today=date(2026, 8, 10),                # fixed "today" so nothing reads as past
        clerk_mailing_date=mailing,
    )
    assert res.deadlines, f"no deadline computed for {method!r}"
    return res.deadlines[0].due_date


def test_personal_served_monday_aug_10_due_aug_17():
    """Personal service Mon 2026-08-10 → 5 business days → Mon 2026-08-17."""
    assert _due("personal", date(2026, 8, 10)) == date(2026, 8, 17)


def test_substitute_delivered_monday_aug_10_due_aug_17():
    """Substitute service (delivery to qualified co-resident, § 48.183(2))
    runs the same day-after + 5-business-day clock as personal service."""
    assert _due("substitute", date(2026, 8, 10)) == date(2026, 8, 17)


def test_substitute_is_an_explicit_branch_not_fallthrough():
    """The substitute method must be declared: the computed deadline carries
    a § 48.183(2) disclosure naming substitute service, proving it went
    through its own branch rather than the generic else."""
    res = compute_deadline_for_event(
        rule_key="eviction_complaint",
        event_date=date(2026, 8, 10),
        service_method="substitute",
        circuit=None,
        closure_dates=frozenset(),
        has_local_closure_data=True,
        today=date(2026, 8, 10),
        clerk_mailing_date=None,
    )
    assert res.deadlines, "no deadline computed"
    d = res.deadlines[0]
    joined = " ".join(d.assumption_disclosures)
    assert "§ 48.183(2)" in joined
    assert "substitute" in joined.lower()


def test_posted_aug_10_mailed_aug_12_due_aug_19():
    """Posted service: effective date is the LATER of posting (08-10) and
    clerk's certificate of mailing (08-12) → 5 business days from 08-12 →
    Wed 2026-08-19. Never computed from the posting date alone."""
    assert _due("posted", date(2026, 8, 10), mailing=date(2026, 8, 12)) == date(2026, 8, 19)
