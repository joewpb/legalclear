"""I-4 — claim state machine tests (deterministic, no IO).

Phase topology under test is the REAL fire content seed (content.loader
loads fire.jsonl from disk), so these tests also pin the content layer's
trigger vocabulary — a content edit that breaks the machine fails here.
"""

from datetime import date, datetime, timezone, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.agents.claim_state import compute_state, phase_status, trigger_vocabulary
from src.content.loader import load_active_content


def _records():
    return load_active_content()


def _ev(name: str, ts: datetime) -> dict:
    return {"trigger_name": name, "occurred_at": ts.isoformat()}


def _claim(date_of_loss: str | None = "2026-08-01") -> dict:
    return {
        "peril": "fire",
        "date_of_loss": date_of_loss,
        "created_at": "2026-08-01T10:00:00+00:00",
    }


BASE = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def _state(events: list[dict], *, now: datetime = BASE) -> dict:
    return compute_state(_claim(), events, _records(), now=now)


def test_vocabulary_covers_every_content_trigger():
    vocab = trigger_vocabulary(_records())
    expected = {
        "date_of_loss", "claim_number_received", "adjuster_inspection_scheduled",
        "carrier_estimate_received", "contents_inventory_submitted",
        "payment_received", "rebuild_complete",
        "claim_denied_or_underpaid", "resolved_or_suit_filed",
    }
    assert vocab >= expected


def test_fresh_claim_only_p0_active():
    state = _state([_ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc))])
    assert state["current_phase"] == "fire.p0.immediate"
    assert state["active_phase_ids"] == ["fire.p0.immediate"]
    assert state["completed_phase_ids"] == []
    assert state["phase_count"] == 7
    assert state["day_number"] == 19  # 2026-08-01 -> 2026-08-20


def test_claim_number_moves_p0_to_completed_and_p1_active():
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_number_received", datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)),
    ]
    state = _state(events)
    assert state["completed_phase_ids"] == ["fire.p0.immediate"]
    assert state["active_phase_ids"] == ["fire.p1.first_week"]
    assert state["current_phase"] == "fire.p1.first_week"


def test_estimate_arrival_activates_contents_and_money_in_parallel():
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_number_received", datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)),
        _ev("adjuster_inspection_scheduled", datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)),
        _ev("carrier_estimate_received", datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc)),
    ]
    state = _state(events)
    # p2 completed; p3 (contents) and p4 (money) both active
    assert state["completed_phase_ids"] == [
        "fire.p0.immediate", "fire.p1.first_week", "fire.p2.adjuster_inspection",
    ]
    assert state["active_phase_ids"] == ["fire.p3.contents_claim", "fire.p4.the_money"]


def test_denial_activates_dispute_ladder():
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_number_received", datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_denied_or_underpaid", datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)),
    ]
    state = _state(events)
    assert "fire.p6.dispute_ladder" in state["active_phase_ids"]
    assert state["current_phase"] == "fire.p1.first_week"  # earliest ACTIVE wins


def test_full_ladder_to_resolution():
    start = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)
    seq = [
        ("date_of_loss", 0), ("claim_number_received", 1),
        ("adjuster_inspection_scheduled", 4), ("carrier_estimate_received", 11),
        ("contents_inventory_submitted", 29), ("payment_received", 39),
        ("rebuild_complete", 199),
    ]
    events = [_ev(n, start + timedelta(days=d)) for n, d in seq]
    state = _state(events, now=datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc))
    assert state["completed_phase_ids"] == [
        "fire.p0.immediate", "fire.p1.first_week", "fire.p2.adjuster_inspection",
        "fire.p3.contents_claim", "fire.p4.the_money", "fire.p5.rebuilding",
    ]
    assert state["active_phase_ids"] == []
    assert state["current_phase"] == "fire.p5.rebuilding"


def test_extended_flag_when_active_past_typical_window():
    # p2 typical window [1,7] days; entered 2026-08-05, now 2026-08-20 -> 15d
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_number_received", datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)),
        _ev("adjuster_inspection_scheduled", datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)),
    ]
    state = _state(events)
    p2 = next(p for p in state["phases"] if p["phase_id"] == "fire.p2.adjuster_inspection")
    assert p2["status"] == "active"
    assert p2["extended"] is True
    p1 = next(p for p in state["phases"] if p["phase_id"] == "fire.p1.first_week")
    assert p1["status"] == "completed"
    assert p1["extended"] is False


def test_unknown_event_names_do_not_affect_status():
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        {"trigger_name": "not_a_real_trigger", "occurred_at": "2026-08-03T00:00:00+00:00"},
    ]
    state = _state(events)
    assert state["active_phase_ids"] == ["fire.p0.immediate"]


def test_day_number_from_creation_when_no_date_of_loss():
    state = compute_state(
        _claim(date_of_loss=None), [], _records(),
        now=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
    )
    assert state["date_of_loss"] is None
    assert state["day_number"] == 19  # from created_at


def test_phase_status_direct():
    rec = next(r for r in _records() if r.phase_id == "fire.p0.immediate")
    assert phase_status(rec, {"claim_number_received": BASE}) == "completed"
    assert phase_status(rec, {"date_of_loss": BASE}) == "active"
    assert phase_status(rec, {}) == "upcoming"


def test_dispute_ladder_exit_resolves():
    events = [
        _ev("date_of_loss", datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_number_received", datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)),
        _ev("claim_denied_or_underpaid", datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)),
        _ev("resolved_or_suit_filed", datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc)),
    ]
    state = _state(events)
    assert "fire.p6.dispute_ladder" in state["completed_phase_ids"]
    assert "fire.p6.dispute_ladder" not in state["active_phase_ids"]
