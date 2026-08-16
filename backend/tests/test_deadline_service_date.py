"""B5-c1 — PUT /api/deadline/{document_id}/service-date.

Endpoint + validation ONLY. No recompute, no deadline writes, no escalation
contract (that is B5-c2's job). Tests assert THIS endpoint's contract
(validation, response shape, DB write calls via mocks) — not B5-b's pipeline
internals, which live on an unmerged branch (fix/b5-b-service-date-core) and
are not present on main.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "testkey123")

from fastapi.testclient import TestClient

from src.api.routers import deadline as deadline_router
from src.api.routes import app
from src.core.config import settings

client = TestClient(app)

DOCUMENT_ID = "doc-1"
OWNING_SESSION = "session-owner"
ATTACKER_SESSION = "session-attacker"
HEADERS = {"x-api-key": settings.API_KEY}


class _FakeQuery:
    def __init__(self, rows, recorder=None):
        self._rows = rows
        self._recorder = recorder
        self._filters = {}

    def select(self, *a, **k):
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def order(self, *a, **k):
        return self

    def update(self, payload):
        if self._recorder is not None:
            self._recorder.append(payload)
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _FakeClient:
    def __init__(self, rows, recorder=None):
        self._rows = rows
        self._recorder = recorder

    def table(self, name):
        return _FakeQuery(self._rows, self._recorder)


class _FakeDB:
    def __init__(self, rows, recorder=None):
        self.client = _FakeClient(rows, recorder)

    def get_document(self, document_id):
        if document_id != DOCUMENT_ID:
            return None
        return {"id": DOCUMENT_ID, "session_id": OWNING_SESSION}


def _put(body, session_id=OWNING_SESSION, headers=HEADERS):
    params = {"session_id": session_id} if session_id is not None else {}
    return client.put(
        f"/api/deadline/{DOCUMENT_ID}/service-date",
        json=body,
        params=params,
        headers=headers,
    )


def test_requires_api_key():
    r = _put({"service_method": "personal", "service_date": "2026-08-01"}, headers={})
    assert r.status_code == 401


def test_rejects_wrong_session(monkeypatch):
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}])
    )
    r = _put(
        {"service_method": "personal", "service_date": "2026-08-01"},
        session_id=ATTACKER_SESSION,
    )
    assert r.status_code == 404


def test_bad_date_format_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal", "service_date": "08/01/2026"})
    assert r.status_code == 422


def test_nonexistent_calendar_date_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal", "service_date": "2026-02-30"})
    assert r.status_code == 422


def test_absurd_past_date_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal", "service_date": "1999-12-31"})
    assert r.status_code == 422


def test_absurd_future_date_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal", "service_date": "2099-01-01"})
    assert r.status_code == 422


def test_invalid_service_method_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "carrier-pigeon", "service_date": "2026-08-01"})
    assert r.status_code == 422


def test_service_date_required(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal"})
    assert r.status_code == 422


def test_posted_without_mailing_date_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "posted", "service_date": "2026-08-01"})
    assert r.status_code == 422
    assert "clerk_mailing_date" in r.json()["detail"]


def test_posted_with_bad_mailing_date_rejected(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({
        "service_method": "posted",
        "service_date": "2026-08-01",
        "clerk_mailing_date": "not-a-date",
    })
    assert r.status_code == 422


def test_posted_with_mailing_date_accepted_but_not_persisted(monkeypatch):
    recorder = []
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}], recorder=recorder)
    )
    r = _put({
        "service_method": "posted",
        "service_date": "2026-08-01",
        "clerk_mailing_date": "2026-08-05",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["service_date_provenance"] == "user_supplied"
    # clerk_mailing_date is echoed in the response for confirmation, but this
    # slice does not persist it — the DB write payload must not include it.
    assert body["clerk_mailing_date"] == "2026-08-05"
    assert "clerk_mailing_date" not in recorder[0]


def test_upsert_writes_user_supplied_provenance(monkeypatch):
    recorder = []
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}], recorder=recorder)
    )
    r = _put({"service_method": "personal", "service_date": "2026-08-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"] == DOCUMENT_ID
    assert body["trigger_event_id"] == "te-1"
    assert body["user_service_date"] == "2026-08-01"
    assert body["user_service_method"] == "personal"
    assert body["service_date_provenance"] == "user_supplied"
    assert len(recorder) == 1
    assert recorder[0] == {
        "user_service_date": "2026-08-01",
        "user_service_method": "personal",
        "service_date_provenance": "user_supplied",
    }


def test_recompute_contract_is_wired(monkeypatch):
    """B5-c2 seam: the endpoint calls _recompute_deadlines after the upsert —
    recompute is complete (not pending) with the refreshed deadline list."""
    async def _fake_pipeline(document_id, text, db):
        return {"deadlines_written": 0, "escalation_needed": False,
                "escalation_reasons": []}

    import deadline.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "run_deadline_pipeline", _fake_pipeline)
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = _put({"service_method": "personal", "service_date": "2026-08-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["recompute"] == "complete"
    assert isinstance(body["deadlines"], list)
    assert body["service_date_provenance"] == "user_supplied"


def test_unknown_method_still_writes_user_supplied_provenance(monkeypatch):
    """B5-c1 has no escalation contract — 'unknown' is validated and stored
    like any other enum value; that decision is B5-c2's job."""
    recorder = []
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}], recorder=recorder)
    )
    r = _put({"service_method": "unknown", "service_date": "2026-08-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["service_date_provenance"] == "user_supplied"
    assert recorder[0]["service_date_provenance"] == "user_supplied"


def test_no_trigger_event_found_returns_404(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[]))
    r = _put({"service_method": "personal", "service_date": "2026-08-01"})
    assert r.status_code == 404


def test_db_unavailable_returns_503(monkeypatch):
    class _NoDB:
        client = None

        def get_document(self, document_id):
            return None

    monkeypatch.setattr(deadline_router, "db", _NoDB())
    r = _put({"service_method": "personal", "service_date": "2026-08-01"})
    assert r.status_code == 503
