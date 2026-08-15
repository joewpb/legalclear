"""S1-4 — IDOR on deadline GETs (routers/deadline.py:43,62).

Before the fix, GET /api/deadline/{document_id}/deadlines (and the
trigger-events sibling) returned any document's data to any caller who
merely knew (or guessed) the document_id — no session ownership check.
These tests pin the fix: a caller must supply the session_id that actually
owns the document, or the endpoint responds 404 exactly like
delete_document (routes.py:227) already does for the analogous DELETE.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "testkey123")

from fastapi.testclient import TestClient

from src.api.routers import deadline as deadline_router
from src.api.routes import app

client = TestClient(app)

DOCUMENT_ID = "doc-1"
OWNING_SESSION = "session-owner"
ATTACKER_SESSION = "session-attacker"


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _FakeQuery(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self.client = _FakeClient(rows)

    def get_document(self, document_id):
        if document_id != DOCUMENT_ID:
            return None
        return {"id": DOCUMENT_ID, "session_id": OWNING_SESSION}


def test_get_deadlines_rejects_wrong_session(monkeypatch):
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "dl-1", "label": "Answer"}])
    )
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/deadlines",
        params={"session_id": ATTACKER_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 404


def test_get_deadlines_allows_owning_session(monkeypatch):
    monkeypatch.setattr(
        deadline_router, "db", _FakeDB(rows=[{"id": "dl-1", "label": "Answer"}])
    )
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/deadlines",
        params={"session_id": OWNING_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    assert r.json()["deadlines"] == [{"id": "dl-1", "label": "Answer"}]


def test_get_trigger_events_rejects_wrong_session(monkeypatch):
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[{"id": "te-1"}]))
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/trigger-events",
        params={"session_id": ATTACKER_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 404
