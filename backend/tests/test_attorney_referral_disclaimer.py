"""B4b-6: attorney_referral.py is the highest UPL-risk surface in the app and
previously shipped with NO disclaimer at all. Every user-facing response path
(chat, submit, user profile CRUD) must now carry the canonical disclaimer via
src.core.upl.apply_disclaimer.

These tests assert equality-with-apply_disclaimer() output rather than
hardcoding disclaimer text, so they survive the B4b-1 canonicalization merge
(fix/b4b-1-canonicalize, unmerged as of this branch) which will change the
disclaimer text/links but not the contract that responses must match
apply_disclaimer(...)["disclaimer"].
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from src.api.routers import attorney_referral
from src.api.routes import app
from src.core.config import settings
from src.core.upl import apply_disclaimer

client = TestClient(app)

_EXPECTED_DISCLAIMER = apply_disclaimer({}, lang="en")["disclaimer"]
_AUTH_HEADERS = {"x-api-key": settings.API_KEY}


class _FakeTable:
    """Minimal chainable stand-in for supabase-py's table() query builder."""

    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, payload):
        return self

    def execute(self):
        class _Result:
            def __init__(self, data):
                self.data = data

        return _Result(self._rows)


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _FakeTable(self._rows)


def test_intake_chat_success_carries_disclaimer(monkeypatch):
    async def _fake_call_ai(messages):
        return "Thanks for sharing that.", "case_type"

    monkeypatch.setattr(attorney_referral, "_call_ai", _fake_call_ai)

    resp = client.post("/api/attorney-referral/intake", json={"conversation": []})

    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == _EXPECTED_DISCLAIMER
    assert body["content"] == "Thanks for sharing that."


def test_intake_chat_ai_outage_fallback_carries_disclaimer(monkeypatch):
    """The hard-fallback branch of _call_ai (no AI provider reachable) still
    returns 200 with real content — an 'error path that returns content' per
    the B4b-6 spec. It must carry the disclaimer too."""

    async def _fake_call_ai(messages):
        return (
            "Thank you for reaching out. I'm having trouble connecting right now.",
            "greeting",
        )

    monkeypatch.setattr(attorney_referral, "_call_ai", _fake_call_ai)

    resp = client.post("/api/attorney-referral/intake", json={"conversation": []})

    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == _EXPECTED_DISCLAIMER


def test_submit_carries_disclaimer(monkeypatch):
    monkeypatch.setattr(attorney_referral, "db", attorney_referral.db)
    monkeypatch.setattr(attorney_referral.db, "client", _FakeClient([]))

    resp = client.post(
        "/api/attorney-referral/submit",
        json={"user_id": "u1", "conversation": [], "intake_summary": "summary"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == _EXPECTED_DISCLAIMER
    assert body["status"] == "pending"


def test_upsert_user_carries_disclaimer(monkeypatch):
    monkeypatch.setattr(
        attorney_referral.db, "client", _FakeClient([{"id": "u1"}])
    )

    resp = client.post(
        "/api/attorney-referral/users",
        json={"email": "person@example.com"},
        headers=_AUTH_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == _EXPECTED_DISCLAIMER


def test_get_user_carries_disclaimer(monkeypatch):
    monkeypatch.setattr(
        attorney_referral.db,
        "client",
        _FakeClient([{"id": "u1", "email": "person@example.com"}]),
    )

    resp = client.get(
        "/api/attorney-referral/users/u1",
        headers=_AUTH_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == _EXPECTED_DISCLAIMER
