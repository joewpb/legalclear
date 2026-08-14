"""Regression test for S2-5c: an event with no usable date must never be
written to trigger_events with an epoch placeholder (1970-01-01).

Run: cd backend && uv run python -m pytest tests/test_pipeline_no_epoch.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from deadline.pipeline import run_deadline_pipeline


class _FakeTable:
    def __init__(self, recorder):
        self._recorder = recorder

    def select(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def insert(self, row):
        self._recorder.append(row)
        return self

    def execute(self):
        return MagicMock(data=[{"id": "fake-id"}])


class _FakeClient:
    def __init__(self):
        self.inserted_rows = []

    def table(self, name):
        return _FakeTable(self.inserted_rows)


def test_missing_date_is_skipped_not_written_as_epoch():
    """Before the fix: pipeline.py:232 wrote event_date='1970-01-01' for any
    event with no extracted date. After the fix: no trigger_event row is
    written at all for that event; the pipeline escalates instead."""
    fake_client = _FakeClient()
    fake_db = MagicMock(client=fake_client)

    no_date_extraction = {
        "events": [{
            "event_type": "issued",
            "event_date": None,
            "service_method": "unknown",
            "document_type": "eviction_complaint",
            "circuit": 20,
            "county": "Lee",
            "case_number": None,
            "raw_text_excerpt": "DATED this 14th day of August, 2026.",
            "confidence": 0.0,
        }],
        "escalation_needed": True,
        "escalation_reason": "date rejected",
    }

    with patch(
        "deadline.pipeline.extract_trigger_events",
        new=AsyncMock(return_value=no_date_extraction),
    ):
        result = asyncio.run(
            run_deadline_pipeline("doc-1", "irrelevant text", fake_db)
        )

    assert result["trigger_events_written"] == 0
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True
    assert not any(
        row.get("event_date") == "1970-01-01" for row in fake_client.inserted_rows
    )
    assert fake_client.inserted_rows == []


if __name__ == "__main__":
    test_missing_date_is_skipped_not_written_as_epoch()
    print("ALL PIPELINE EPOCH TESTS PASSED")
