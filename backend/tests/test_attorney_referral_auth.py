"""S1-3: /api/attorney-referral/users (POST) and /users/{id} (GET) must require
the standard API-key dependency — previously anyone could read any profile by UUID
or overwrite any profile by supplying its email.

db.client is monkeypatched to None so these tests only exercise the auth
dependency, not a real Supabase connection.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.routers import attorney_referral
from src.api.routes import app
from src.core.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_db(monkeypatch):
    monkeypatch.setattr(attorney_referral.db, "client", None)


def test_upsert_user_requires_api_key():
    r = client.post("/api/attorney-referral/users", json={"email": "victim@example.com"})
    assert r.status_code == 401


def test_get_user_requires_api_key():
    r = client.get("/api/attorney-referral/users/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401


def test_upsert_user_wrong_key_rejected():
    r = client.post(
        "/api/attorney-referral/users",
        json={"email": "victim@example.com"},
        headers={"x-api-key": "wrong"},
    )
    assert r.status_code == 401


def test_get_user_accepts_valid_key():
    r = client.get(
        "/api/attorney-referral/users/00000000-0000-0000-0000-000000000000",
        headers={"x-api-key": settings.API_KEY},
    )
    # Auth passes; downstream 503 (db.client is None) is fine — 401 is not.
    assert r.status_code != 401


def test_intake_requires_api_key():
    r = client.post("/api/attorney-referral/intake", json={"conversation": []})
    assert r.status_code == 401


def test_intake_accepts_valid_key(monkeypatch):
    async def _fake_call_ai(messages):
        return "Thanks.", "case_type"

    monkeypatch.setattr(attorney_referral, "_call_ai", _fake_call_ai)

    r = client.post(
        "/api/attorney-referral/intake",
        json={"conversation": []},
        headers={"x-api-key": settings.API_KEY},
    )
    assert r.status_code == 200


def test_submit_requires_api_key():
    r = client.post(
        "/api/attorney-referral/submit",
        json={"user_id": "u1", "conversation": [], "intake_summary": "summary"},
    )
    assert r.status_code == 401


def test_submit_wrong_key_rejected():
    r = client.post(
        "/api/attorney-referral/submit",
        json={"user_id": "u1", "conversation": [], "intake_summary": "summary"},
        headers={"x-api-key": "wrong"},
    )
    assert r.status_code == 401
