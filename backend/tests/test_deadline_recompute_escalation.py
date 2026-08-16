"""B5-c2 — recompute + escalation contract for the service-date seam.

Pins two behaviors for `_recompute_deadlines` (src/api/routers/deadline.py),
the helper the B5-c1 PUT /api/deadline/{document_id}/service-date endpoint
will call at merge time:

1. Recompute-on-supply / recompute-on-edit: a known service method re-runs
   the deadline pipeline and returns the refreshed deadlines. Edit uses the
   exact same call path as initial supply (upsert semantics upstream).
2. I-don't-know contract (Decision 2) and posted-without-mailing-date
   (Decision 6): both escalate with guidance text and write zero deadline
   rows — no pipeline call at all.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "testkey123")

import deadline.pipeline as pipeline_mod
from src.api.routers import deadline as deadline_router

DOCUMENT_ID = "doc-1"


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _RecordingQuery:
    """Records every insert so tests can assert zero deadline writes."""

    def __init__(self, table_name, inserts, select_rows):
        self._table_name = table_name
        self._inserts = inserts
        self._select_rows = select_rows

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self._inserts.append((self._table_name, row))
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        if self._table_name == "deadlines" and not self._inserts_are_write():
            return _FakeResult(self._select_rows)
        if self._table_name == "trigger_events":
            return _FakeResult([{"id": "trigger-1"}])
        if self._table_name == "court_closures":
            return _FakeResult([])
        return _FakeResult([{"id": "row-1"}])

    def _inserts_are_write(self):
        return False


class _FakeClient:
    def __init__(self, inserts, select_rows):
        self._inserts = inserts
        self._select_rows = select_rows

    def table(self, name):
        return _RecordingQuery(name, self._inserts, self._select_rows)


class _FakeDb:
    def __init__(self, inserts, select_rows, document_text="Some document text."):
        self.client = _FakeClient(inserts, select_rows)
        self._document_text = document_text

    def get_document(self, document_id):
        return {"id": document_id, "document_text": self._document_text}


EVENT = {
    "document_type": "civil_summons",
    "event_date": "2026-04-01",
    "service_method": "personal",
    "confidence": 0.95,
    "circuit": 13,
    "event_type": "served",
}


def _patch_extract(monkeypatch, events):
    async def _fake_extract(document_text):
        return {"events": events, "escalation_needed": False, "escalation_reason": None}

    monkeypatch.setattr(pipeline_mod, "extract_trigger_events", _fake_extract)


def test_supply_recompute_returns_deadlines(monkeypatch):
    _patch_extract(monkeypatch, [dict(EVENT)])
    inserts = []
    fake_db = _FakeDb(inserts, select_rows=[{"id": "dl-1", "label": "Answer"}])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    result = asyncio.run(
        deadline_router._recompute_deadlines(DOCUMENT_ID, service_method="personal")
    )

    assert result["recompute"] == "complete"
    assert result["deadlines"] == [{"id": "dl-1", "label": "Answer"}]
    assert any(t == "deadlines" for t, _ in inserts), "expected a deadline row to be written"


def test_edit_recompute_returns_updated_deadlines(monkeypatch):
    """Edit takes the same helper path as supply — no separate branch."""
    _patch_extract(monkeypatch, [dict(EVENT)])
    inserts = []
    fake_db = _FakeDb(inserts, select_rows=[{"id": "dl-1", "label": "Answer (updated)"}])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    first = asyncio.run(
        deadline_router._recompute_deadlines(DOCUMENT_ID, service_method="personal")
    )
    second = asyncio.run(
        deadline_router._recompute_deadlines(DOCUMENT_ID, service_method="mail")
    )

    assert first["recompute"] == "complete"
    assert second["recompute"] == "complete"
    assert second["deadlines"] == [{"id": "dl-1", "label": "Answer (updated)"}]


def test_unknown_service_method_escalates_with_zero_deadline_writes(monkeypatch):
    _patch_extract(monkeypatch, [dict(EVENT)])
    inserts = []
    fake_db = _FakeDb(inserts, select_rows=[])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    called = {"pipeline": False}

    async def _fail_if_called(*a, **k):
        called["pipeline"] = True
        raise AssertionError("pipeline must not run for unknown service method")

    monkeypatch.setattr(pipeline_mod, "run_deadline_pipeline", _fail_if_called)

    result = asyncio.run(
        deadline_router._recompute_deadlines(DOCUMENT_ID, service_method="unknown")
    )

    assert result["recompute"] == "escalated"
    assert result["escalation_needed"] is True
    assert result["deadlines"] == []
    assert "clerk" in result["guidance"].lower()
    assert "docket" in result["guidance"].lower()
    assert called["pipeline"] is False
    assert not any(t == "deadlines" for t, _ in inserts), "must write zero deadline rows"


def test_missing_service_method_escalates(monkeypatch):
    fake_db = _FakeDb([], select_rows=[])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    result = asyncio.run(
        deadline_router._recompute_deadlines(DOCUMENT_ID, service_method=None)
    )

    assert result["recompute"] == "escalated"
    assert result["deadlines"] == []


def test_posted_without_mailing_date_escalates_with_zero_deadline_writes(monkeypatch):
    _patch_extract(monkeypatch, [dict(EVENT)])
    inserts = []
    fake_db = _FakeDb(inserts, select_rows=[])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    async def _fail_if_called(*a, **k):
        raise AssertionError("pipeline must not run for posted service without a mailing date")

    monkeypatch.setattr(pipeline_mod, "run_deadline_pipeline", _fail_if_called)

    result = asyncio.run(
        deadline_router._recompute_deadlines(
            DOCUMENT_ID, service_method="posted", clerk_mailing_date=None
        )
    )

    assert result["recompute"] == "escalated"
    assert result["escalation_needed"] is True
    assert result["deadlines"] == []
    assert "mailing date" in result["guidance"].lower()
    assert not any(t == "deadlines" for t, _ in inserts), "must write zero deadline rows"


def test_posted_with_mailing_date_recomputes(monkeypatch):
    _patch_extract(monkeypatch, [dict(EVENT)])
    inserts = []
    fake_db = _FakeDb(inserts, select_rows=[{"id": "dl-2"}])
    monkeypatch.setattr(deadline_router, "db", fake_db)

    result = asyncio.run(
        deadline_router._recompute_deadlines(
            DOCUMENT_ID, service_method="posted", clerk_mailing_date="2026-04-05"
        )
    )

    assert result["recompute"] == "complete"
    assert result["deadlines"] == [{"id": "dl-2"}]
