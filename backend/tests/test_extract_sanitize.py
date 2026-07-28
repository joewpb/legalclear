"""Unit tests for the extract-stage anti-hallucination guard.

These tests are pure Python: no LLM calls, no DB calls. They lock in the
behaviour added for issue #49 — a fabricated placeholder date (e.g.
2025-01-01) returned by the extractor must be deterministically discarded
and escalated rather than flowing into the deadline computation.

Run: cd backend && uv run python -m pytest tests/test_extract_sanitize.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deadline.extract import _date_appears_in_text, _sanitize_events


# ── _date_appears_in_text ───────────────────────────────────────────────────

def test_iso_date_present():
    assert _date_appears_in_text("2025-03-07", "hearing on 2025-03-07 at 9am")


def test_us_numeric_slash():
    assert _date_appears_in_text("2025-03-07", "filed 03/07/2025")
    assert _date_appears_in_text("2025-01-09", "filed 1/9/2025")


def test_us_numeric_dash():
    assert _date_appears_in_text("2025-03-07", "filed 03-07-2025")


def test_full_month_name():
    assert _date_appears_in_text("2025-03-07", "on March 7, 2025")
    assert _date_appears_in_text("2025-03-07", "on March 7 2025")


def test_abbrev_month():
    assert _date_appears_in_text("2025-03-07", "on Mar 7, 2025")
    assert _date_appears_in_text("2025-01-09", "on Jan. 9, 2025".replace(".", ""))


def test_absent_date_returns_false():
    assert not _date_appears_in_text("2025-01-01", "no dates anywhere in this text")


def test_placeholder_jan_1_absent_returns_false():
    # The classic hallucination: a Jan 1 placeholder that is NOT in the doc.
    assert not _date_appears_in_text(
        "2025-01-01", "Small Claims Summons — pretrial to be scheduled."
    )


def test_invalid_iso_returns_false():
    assert not _date_appears_in_text("not-a-date", "whatever")
    assert not _date_appears_in_text(None, "whatever")


# ── _sanitize_events ────────────────────────────────────────────────────────

def test_hallucinated_date_is_nullified_and_escalated():
    data = {
        "events": [{
            "event_type": "issued",
            "event_date": "2025-01-01",   # fabricated — not in the doc
            "service_method": "unknown",
            "document_type": "small_claims_summons",
            "raw_text_excerpt": "Small Claims Summons",
            "confidence": 0.8,
        }],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    doc = "IN THE COUNTY COURT — Small Claims Summons. Pretrial date TBD by clerk."

    out = _sanitize_events(data, doc)

    assert out["events"][0]["event_date"] is None
    assert out["events"][0]["confidence"] == 0.0
    assert out["escalation_needed"] is True
    assert "hallucination" in out["escalation_reason"]


def test_real_date_is_preserved():
    data = {
        "events": [{
            "event_type": "served",
            "event_date": "2026-04-15",
            "service_method": "personal",
            "document_type": "civil_summons",
            "raw_text_excerpt": "served on April 15, 2026",
            "confidence": 0.95,
        }],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    doc = "You were served on April 15, 2026 by the sheriff."

    out = _sanitize_events(data, doc)

    assert out["events"][0]["event_date"] == "2026-04-15"
    assert out["events"][0]["confidence"] == 0.95
    assert out["escalation_needed"] is False


def test_already_null_date_is_left_alone():
    data = {
        "events": [{
            "event_type": "unknown",
            "event_date": None,
            "service_method": "unknown",
            "document_type": "small_claims_summons",
            "raw_text_excerpt": "",
            "confidence": 0.3,
        }],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    out = _sanitize_events(data, "no date here")
    assert out["events"][0]["event_date"] is None
    assert out["escalation_needed"] is False


def test_mixed_events_only_bad_one_nulled():
    data = {
        "events": [
            {"event_date": "2026-04-15", "confidence": 0.9},
            {"event_date": "2025-01-01", "confidence": 0.7},  # hallucinated
        ],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    doc = "Service occurred on 04/15/2026."
    out = _sanitize_events(data, doc)
    assert out["events"][0]["event_date"] == "2026-04-15"
    assert out["events"][1]["event_date"] is None
    assert out["escalation_needed"] is True


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"  ok — {name}")
    print("ALL SANITIZE TESTS PASSED")
