"""Unit tests for the deadline pipeline orchestrator — S3-4 regression.

Stage 1 (LLM extraction) is stubbed; only the closure-fetch failure path and
its effect on escalation are under test.

Run: cd backend && uv run python -m pytest tests/test_deadline_pipeline.py -v
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import deadline.pipeline as pipeline_mod

EVENT = {
    "document_type": "civil_summons",
    "event_date": "2026-04-01",
    "service_method": "personal",
    "confidence": 0.95,
    "circuit": 13,
    # "served" is the schema enum value (extract.py); civil_summons requires a
    # service anchor (S2-7) — an off-schema label would now escalate instead.
    "event_type": "served",
}


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, table_name, fail_tables):
        self._table_name = table_name
        self._fail_tables = fail_tables

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self._row = row
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        if self._table_name in self._fail_tables:
            raise RuntimeError("simulated closure fetch failure")
        if self._table_name == "trigger_events":
            return _FakeResult([{"id": "trigger-1"}])
        if self._table_name == "court_closures":
            return _FakeResult([])
        return _FakeResult([{"id": "row-1"}])


class _FakeClient:
    def __init__(self, fail_tables):
        self._fail_tables = fail_tables

    def table(self, name):
        return _FakeQuery(name, self._fail_tables)


class _FakeDb:
    def __init__(self, fail_tables):
        self.client = _FakeClient(fail_tables)

    def get_user_supplied_service_date(self, document_id, event_type):
        # No user-supplied date in these pipeline tests: the extracted event
        # date stays the anchor, preserving pre-B5 expectations.
        return None


def _run_pipeline(fail_tables, monkeypatch):
    async def _fake_extract(document_text):
        return {"events": [dict(EVENT)], "escalation_needed": False, "escalation_reason": None}

    monkeypatch.setattr(pipeline_mod, "extract_trigger_events", _fake_extract)
    db = _FakeDb(fail_tables)
    return asyncio.run(pipeline_mod.run_deadline_pipeline("doc-1", "some text", db))


def test_closure_fetch_success_does_not_force_escalation(monkeypatch):
    """Baseline: closure fetch succeeds → no forced escalation from this path."""
    result = _run_pipeline(fail_tables=set(), monkeypatch=monkeypatch)
    assert result["deadlines_written"] == 1
    assert not any(
        "could not be retrieved" in r for r in result["escalation_reasons"]
    )


def test_closure_fetch_failure_escalates_instead_of_silent_compute(monkeypatch):
    """S3-4: closure fetch failure must not silently compute a deadline.

    Before the fix, an exception fetching court_closures was swallowed (logged
    only) and the pipeline proceeded to compute and write the deadline as if
    closures were known/absent — a silently-wrong legal deadline.
    """
    result = _run_pipeline(fail_tables={"court_closures"}, monkeypatch=monkeypatch)

    assert result["deadlines_written"] == 1
    assert result["escalation_needed"] is True
    assert any(
        "could not be retrieved" in r for r in result["escalation_reasons"]
    ), result["escalation_reasons"]


# ── S3-5d: insert failures must surface, never be reported as success ───────

def test_trigger_event_insert_failure_does_not_claim_success(monkeypatch):
    """A failed trigger_events insert must not be counted as written, and
    must escalate — before the fix, trigger_events_written was incremented
    unconditionally regardless of whether the insert actually succeeded."""
    result = _run_pipeline(fail_tables={"trigger_events"}, monkeypatch=monkeypatch)

    assert result["trigger_events_written"] == 0
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True
    assert any(
        "trigger event" in r.lower() and "could not be saved" in r.lower()
        for r in result["escalation_reasons"]
    ), result["escalation_reasons"]


def test_deadline_insert_failure_does_not_claim_success(monkeypatch):
    """A failed deadlines insert must not be counted as written, and must
    escalate — the trigger event (written successfully) is still counted,
    reporting partial success truthfully rather than a blanket 200."""
    result = _run_pipeline(fail_tables={"deadlines"}, monkeypatch=monkeypatch)

    assert result["trigger_events_written"] == 1
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True
    assert any(
        "deadline" in r.lower() and "could not be saved" in r.lower()
        for r in result["escalation_reasons"]
    ), result["escalation_reasons"]
