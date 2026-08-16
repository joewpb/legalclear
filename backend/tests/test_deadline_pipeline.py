"""Unit tests for the deadline pipeline orchestrator — S3-4 regression.

Stage 1 (LLM extraction) is stubbed; only the closure-fetch failure path and
its effect on escalation are under test.

Run: cd backend && uv run python -m pytest tests/test_deadline_pipeline.py -v
"""

import asyncio
import sys
import os
from datetime import date

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
    def __init__(self, table_name, fail_tables, client):
        self._table_name = table_name
        self._fail_tables = fail_tables
        self._client = client
        self._row = None
        self._is_delete = False

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self._row = row
        return self

    def delete(self):
        self._is_delete = True
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        if self._table_name in self._fail_tables:
            raise RuntimeError("simulated closure fetch failure")
        if self._is_delete:
            # B5-f2 Contract 2: recompute must supersede prior deadline rows
            # for the document, not accumulate — tests assert on what
            # survives in `self._client.live_deadlines` after a delete.
            if self._table_name == "deadlines":
                self._client.live_deadlines = []
            return _FakeResult([])
        if self._row is not None:
            # B5-f regression tests inspect what was actually inserted, to
            # assert which anchor date the pipeline fed into computation —
            # not just the summary counts.
            self._client.inserted.setdefault(self._table_name, []).append(self._row)
            if self._table_name == "deadlines":
                self._client.live_deadlines.append(self._row)
        if self._table_name == "trigger_events":
            return _FakeResult([{"id": "trigger-1"}])
        if self._table_name == "court_closures":
            return _FakeResult([])
        return _FakeResult([{"id": "row-1"}])


class _FakeClient:
    def __init__(self, fail_tables):
        self._fail_tables = fail_tables
        self.inserted = {}
        # Rows that would still be live in the "deadlines" table after any
        # delete-then-insert supersede calls so far — persists across
        # multiple pipeline runs against the same _FakeDb/_FakeClient, so
        # tests can simulate two sequential recomputes.
        self.live_deadlines = []

    def table(self, name):
        return _FakeQuery(name, self._fail_tables, self)


class _FakeDb:
    def __init__(self, fail_tables, user_supplied=None):
        self.client = _FakeClient(fail_tables)
        # B5-f3: dict with service_date / service_method / clerk_mailing_date,
        # or None — simulates the document_service_facts row a prior PUT
        # .../service-date call would have left. The pipeline only ever reads
        # this via get_document_service_fact — no write method exists on this
        # fake, so any pipeline attempt to write it fails the test loudly.
        self._user_supplied = user_supplied

    def get_document_service_fact(self, document_id):
        # No user-supplied fact by default: the extracted event date stays
        # the anchor, preserving pre-B5 expectations.
        return self._user_supplied


def _run_pipeline(fail_tables, monkeypatch, event=None, user_supplied=None):
    result, _db = _run_pipeline_with_db(fail_tables, monkeypatch, event=event, user_supplied=user_supplied)
    return result


def _run_pipeline_with_db(fail_tables, monkeypatch, event=None, user_supplied=None, db=None):
    async def _fake_extract(document_text):
        return {"events": [dict(event or EVENT)], "escalation_needed": False, "escalation_reason": None}

    monkeypatch.setattr(pipeline_mod, "extract_trigger_events", _fake_extract)
    if db is None:
        db = _FakeDb(fail_tables, user_supplied=user_supplied)
    else:
        db._user_supplied = user_supplied
    result = asyncio.run(pipeline_mod.run_deadline_pipeline("doc-1", "some text", db))
    return result, db


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


# ── B5-f: user-supplied service date must WIN in run_deadline_pipeline ──────
# Reproduces the live defect: extraction yields only an "issued" date (never
# "served"), so the anchor-mismatch gate used to escalate and `continue`
# before the user-supplied date was ever consulted. These tests exercise
# run_deadline_pipeline end-to-end (not compute_deadline_for_event directly)
# so a regression in the pipeline's *ordering* — not just the compute
# function B5-b already covers — fails the suite.

EVICTION_EVENT_ISSUED = {
    "document_type": "eviction_complaint",
    "event_date": "2026-08-14",   # extracted "issued" date — must NOT be the anchor
    "service_method": "personal",
    "confidence": 0.95,
    "circuit": 13,
    "event_type": "issued",
}


def _expected_due_date(event_date, service_method, clerk_mailing_date=None):
    from deadline.compute import compute_deadline_for_event
    result = compute_deadline_for_event(
        rule_key="eviction_complaint",
        event_date=event_date,
        service_method=service_method,
        circuit=13,
        closure_dates=frozenset(),
        has_local_closure_data=False,
        clerk_mailing_date=clerk_mailing_date,
    )
    return result.deadlines[0].due_date


def test_user_supplied_personal_service_date_wins_over_extracted_issued_date(monkeypatch):
    """Personal service: user supplied 08-10; extraction only found "issued" 08-14.

    The deadline must be computed from 08-10 (the user-supplied anchor), not
    08-14 (the extracted issuance date) — Decision 2.
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="personal")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "personal",
        "clerk_mailing_date": None,
    }
    result, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 1
    expected_due = _expected_due_date(date(2026, 8, 10), "personal")
    written = db.client.inserted["deadlines"][0]
    assert written["due_date"] == expected_due.isoformat()
    trace_dates = [step.get("date") for step in written["computation_trace"]]
    assert "2026-08-10" in trace_dates
    assert "2026-08-14" not in trace_dates


def test_user_supplied_posted_service_uses_later_of_posting_and_mailing(monkeypatch):
    """Posted service: user supplied posting 08-10 + clerk mailing 08-12.

    Decision 6: the anchor is the later of the two (08-12 here), never the
    extracted "issued" date (08-14).
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="posted")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "posted",
        "clerk_mailing_date": "2026-08-12",
    }
    result, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 1
    expected_due = _expected_due_date(
        date(2026, 8, 10), "posted", clerk_mailing_date=date(2026, 8, 12),
    )
    written = db.client.inserted["deadlines"][0]
    assert written["due_date"] == expected_due.isoformat()
    trace_dates = [step.get("date") for step in written["computation_trace"]]
    assert "2026-08-12" in trace_dates
    assert "2026-08-14" not in trace_dates


def test_user_supplied_posted_service_without_clerk_mailing_date_escalates(monkeypatch):
    """Posted service with a posting date but no persisted clerk_mailing_date
    must escalate with zero deadlines (Decision 6) — never compute from the
    posting date alone."""
    event = dict(EVICTION_EVENT_ISSUED, service_method="posted")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "posted",
        "clerk_mailing_date": None,
    }
    result = _run_pipeline(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True
    assert any(
        "certificate-of-mailing" in r.lower() or "mailing date" in r.lower()
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


# ── B5-f2: the user-supplied record wins AS A UNIT (method, not just date) ──
# Live defect (doc 56703e4b): a PUT posted-service call persisted posting
# 08-10 / mailing 08-12, but recompute fed the freshly EXTRACTED
# service_method ("unknown") into computation instead of the persisted
# user_service_method ("posted") — later-of (Decision 6) never fired and the
# deadline was computed from the posting date via the conservative
# unknown-method path. These tests exercise run_deadline_pipeline end-to-end.

def test_user_supplied_method_wins_over_extracted_unknown_method(monkeypatch):
    """Extraction reports service_method "unknown"; the user has persisted
    "posted" service (posting 08-10, mailing 08-12). The unit record must
    override the method too, not just the date — later-of fires and the
    deadline is computed from the mailing date (08-12), never treated as
    unknown-method.
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="unknown")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "posted",
        "clerk_mailing_date": "2026-08-12",
    }
    result, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 1
    expected_due = _expected_due_date(
        date(2026, 8, 10), "posted", clerk_mailing_date=date(2026, 8, 12),
    )
    written = db.client.inserted["deadlines"][0]
    assert written["due_date"] == expected_due.isoformat()
    trace_dates = [step.get("date") for step in written["computation_trace"]]
    assert "2026-08-12" in trace_dates
    assert "2026-08-14" not in trace_dates


def test_recompute_supersedes_prior_deadline_row(monkeypatch):
    """Two recomputes of the same document with different user-supplied
    dates must leave exactly ONE live deadline row — the second recompute
    supersedes the first rather than accumulating alongside it (Contract 2).
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="personal")
    first_supplied = {
        "service_date": "2026-08-10",
        "service_method": "personal",
        "clerk_mailing_date": None,
    }
    second_supplied = {
        "service_date": "2026-08-11",
        "service_method": "personal",
        "clerk_mailing_date": None,
    }

    _, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=first_supplied,
    )
    assert len(db.client.live_deadlines) == 1
    first_due = db.client.live_deadlines[0]["due_date"]

    result2, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=second_supplied, db=db,
    )

    assert result2["deadlines_written"] == 1
    assert len(db.client.live_deadlines) == 1
    assert db.client.live_deadlines[0]["due_date"] != first_due


def test_user_supplied_provenance_excludes_extracted_date_and_method_from_trace(monkeypatch):
    """provenance user_supplied → no extracted date or extracted method may
    appear anywhere in the computation trace — the trace must reflect only
    the user-supplied unit record.
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="unknown")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "posted",
        "clerk_mailing_date": "2026-08-12",
    }
    result, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 1
    written = db.client.inserted["deadlines"][0]
    trace_str = str(written["computation_trace"])
    assert "2026-08-14" not in trace_str  # extracted "issued" date
    assert "unknown" not in trace_str.lower()  # extracted service_method


def test_recompute_never_writes_document_service_facts(monkeypatch):
    """B5-f3's core regression: a full recompute cycle must leave the
    document_service_facts row byte-for-byte unchanged — the pipeline only
    ever reads it (via get_document_service_fact). _FakeDb defines no write
    method for this table, so if the pipeline ever attempted to write it,
    this test would fail with an AttributeError rather than silently pass.
    This is the assertion that would have caught all four prior variants of
    the trigger_events-clobbering bug.
    """
    event = dict(EVICTION_EVENT_ISSUED, service_method="unknown")
    user_supplied = {
        "service_date": "2026-08-10",
        "service_method": "posted",
        "clerk_mailing_date": "2026-08-12",
    }
    before = dict(user_supplied)

    result, db = _run_pipeline_with_db(
        fail_tables=set(), monkeypatch=monkeypatch, event=event, user_supplied=user_supplied,
    )

    assert result["deadlines_written"] == 1
    assert db.get_document_service_fact("doc-1") == before
