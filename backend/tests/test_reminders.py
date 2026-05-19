"""Unit tests for reminder schedule logic — Phase 6.

Pure Python — no DB, no network, no Expo calls.

Run: cd backend && uv run python -m pytest tests/test_reminders.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime, timedelta, timezone

from src.core.reminders import (
    URGENT_HOURS,
    compute_reminder_schedule,
    get_copy,
)

UTC = timezone.utc


def _now(days_before_due: float, due: date | None = None) -> datetime:
    """Return a 'now' that is `days_before_due` days before the due date."""
    due = due or date(2026, 6, 1)
    due_dt = datetime(due.year, due.month, due.day, 17, 0, 0, tzinfo=UTC)
    return due_dt - timedelta(days=days_before_due)


DUE = date(2026, 6, 1)


# ── Fatal severity — full schedule ───────────────────────────────────────────

def test_fatal_full_schedule():
    """Fatal deadline 30 days out → 14d, 7d, 3d, 1d reminders."""
    specs = compute_reminder_schedule(DUE, "fatal", _now(30))
    types = [s.type for s in specs]
    assert "14d" in types
    assert "7d" in types
    assert "3d" in types
    assert "1d" in types


def test_fatal_12_days_out_skips_14d():
    """Fatal, 12 days out → 14d already past, schedule starts at 7d."""
    specs = compute_reminder_schedule(DUE, "fatal", _now(12))
    types = [s.type for s in specs]
    assert "14d" not in types
    assert "7d" in types


def test_fatal_5_days_out_starts_at_3d():
    """Fatal, 5 days out → 14d and 7d already past."""
    specs = compute_reminder_schedule(DUE, "fatal", _now(5))
    types = [s.type for s in specs]
    assert "14d" not in types
    assert "7d" not in types
    assert "3d" in types
    assert "1d" in types


# ── Severity scaling ──────────────────────────────────────────────────────────

def test_high_severity_starts_at_7d():
    specs = compute_reminder_schedule(DUE, "high", _now(30))
    types = [s.type for s in specs]
    assert "14d" not in types
    assert "7d" in types
    assert "1d" in types


def test_medium_severity_starts_at_3d():
    specs = compute_reminder_schedule(DUE, "medium", _now(30))
    types = [s.type for s in specs]
    assert "14d" not in types
    assert "7d" not in types
    assert "3d" in types


def test_low_severity_only_1d():
    specs = compute_reminder_schedule(DUE, "low", _now(30))
    types = [s.type for s in specs]
    assert types == ["1d"]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_past_deadline_returns_empty():
    """A past deadline returns no future reminders — caller marks expired."""
    past = _now(-1)   # 1 day AFTER the due date
    specs = compute_reminder_schedule(DUE, "fatal", past)
    assert specs == []


def test_urgent_window_returns_urgent():
    """Within URGENT_HOURS hours → urgent reminder, no standard reminders."""
    now = _now(URGENT_HOURS / 24 - 0.1)   # just inside the urgent window
    specs = compute_reminder_schedule(DUE, "fatal", now)
    assert len(specs) == 1
    assert specs[0].type == "urgent"


def test_urgent_fire_at_is_near_future():
    """Urgent reminder fires within 10 minutes."""
    now = _now(0.1)
    specs = compute_reminder_schedule(DUE, "fatal", now)
    assert specs[0].type == "urgent"
    delta = (specs[0].fire_at - now).total_seconds()
    assert 0 < delta < 600   # fires within 10 minutes


def test_fire_at_is_in_future():
    """All scheduled reminders must have fire_at > now."""
    now = _now(30)
    specs = compute_reminder_schedule(DUE, "fatal", now)
    for spec in specs:
        assert spec.fire_at > now, f"Reminder {spec.type} has fire_at in the past"


# ── Notification copy ─────────────────────────────────────────────────────────

def test_copy_english_has_required_keys():
    for rtype in ("14d", "7d", "3d", "1d", "urgent", "expired"):
        copy = get_copy(rtype, "en")
        assert "title" in copy
        assert "body" in copy


def test_copy_spanish_has_required_keys():
    for rtype in ("14d", "7d", "3d", "1d", "urgent", "expired"):
        copy = get_copy(rtype, "es")
        assert "title" in copy
        assert "body" in copy


def test_expired_copy_does_not_imply_time_remains():
    """Expired copy must never say 'you have time'."""
    for lang in ("en", "es"):
        copy = get_copy("expired", lang)
        body_lower = copy["body"].lower()
        assert "time" not in body_lower or "passed" in body_lower, (
            f"Expired copy in {lang!r} may imply time remains: {copy['body']}"
        )


def test_unknown_lang_falls_back_to_english():
    copy_unknown = get_copy("1d", "fr")
    copy_en = get_copy("1d", "en")
    assert copy_unknown == copy_en
