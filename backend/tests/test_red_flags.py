"""I-6 — red-flag detector tests (deterministic, no IO)."""

from datetime import datetime, timezone, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.red_flags import (
    USER_DECLARED_FLAGS,
    active_flags,
    derived_flags,
    escalation,
    user_declared_flags,
)

BASE = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def _ev(name: str, ts: datetime) -> dict:
    return {"trigger_name": name, "occurred_at": ts.isoformat()}


def _ago(days: int) -> datetime:
    return BASE - timedelta(days=days)


def test_no_flags_no_escalation():
    assert escalation(active_flags([], now=BASE)) is None


def test_single_flag_no_escalation():
    events = [_ev("reservation_of_rights_letter", _ago(1))]
    assert len(user_declared_flags(events)) == 1
    assert escalation(active_flags(events, now=BASE)) is None


def test_two_user_flags_escalate_without_financial_screen():
    events = [
        _ev("reservation_of_rights_letter", _ago(3)),
        _ev("euo_demanded", _ago(1)),
    ]
    payload = escalation(active_flags(events, now=BASE))
    assert payload is not None
    assert payload["active_count"] == 2
    assert payload["show_financial_screen"] is False
    assert payload["financial_screen_text"] is None
    assert payload["resource_links"] and payload["resource_links"][0]["url"] == "/find-legal-help"


def test_financial_flag_shows_special_screen():
    events = [
        _ev("financial_records_demanded", _ago(2)),
        _ev("siu_contact", _ago(1)),
    ]
    payload = escalation(active_flags(events, now=BASE))
    assert payload is not None
    assert payload["show_financial_screen"] is True
    assert "Do not refuse." in payload["financial_screen_text"]
    assert "Do not sign a blank authorization either." in payload["financial_screen_text"]


def test_derived_no_estimate_after_inspection():
    events = [_ev("adjuster_inspection_scheduled", _ago(8))]
    flags = derived_flags(events, now=BASE)
    assert [f["name"] for f in flags] == ["no_estimate_7d_after_inspection"]


def test_derived_no_estimate_not_triggered_before_7_days():
    events = [_ev("adjuster_inspection_scheduled", _ago(3))]
    assert derived_flags(events, now=BASE) == []


def test_estimate_arrival_cancels_no_estimate_flag():
    events = [
        _ev("adjuster_inspection_scheduled", _ago(10)),
        _ev("carrier_estimate_received", _ago(2)),
    ]
    assert derived_flags(events, now=BASE) == []


def test_derived_silence_past_day_60():
    events = [_ev("claim_number_received", _ago(61))]
    flags = derived_flags(events, now=BASE)
    assert [f["name"] for f in flags] == ["silence_past_day_60"]


def test_silence_flag_cleared_by_payment():
    events = [
        _ev("claim_number_received", _ago(61)),
        _ev("payment_received", _ago(1)),
    ]
    assert derived_flags(events, now=BASE) == []


def test_silence_flag_cleared_by_denial():
    events = [
        _ev("claim_number_received", _ago(61)),
        _ev("claim_denied_or_underpaid", _ago(1)),
    ]
    assert derived_flags(events, now=BASE) == []


def test_derived_flag_alone_does_not_escalate():
    events = [_ev("adjuster_inspection_scheduled", _ago(8))]
    assert escalation(active_flags(events, now=BASE)) is None


def test_derived_plus_user_flag_escalates():
    events = [
        _ev("adjuster_inspection_scheduled", _ago(8)),
        _ev("reservation_of_rights_letter", _ago(2)),
    ]
    payload = escalation(active_flags(events, now=BASE))
    assert payload is not None
    assert payload["active_count"] == 2


def test_flag_catalog_is_complete():
    names = {f["name"] for f in USER_DECLARED_FLAGS}
    assert names == {
        "reservation_of_rights_letter", "recorded_statement_re_requested",
        "siu_contact", "financial_records_demanded", "euo_demanded",
        "engineer_retained", "third_adjuster_assigned",
        "estimate_omits_scope", "full_and_final_check",
    }


def test_user_declared_flags_ignore_phase_triggers():
    events = [
        _ev("claim_number_received", _ago(2)),   # phase trigger, not a flag
        _ev("reservation_of_rights_letter", _ago(1)),
    ]
    flags = user_declared_flags(events)
    assert [f["name"] for f in flags] == ["reservation_of_rights_letter"]
