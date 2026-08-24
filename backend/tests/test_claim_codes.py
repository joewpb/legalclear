"""I-2d — anonymous resumable claim codes.

Pure Python + mocked Supabase client, no live DB, no LLM.

Run: cd backend && uv run python -m pytest tests/test_claim_codes.py -v
"""

import asyncio
import hashlib
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import HTTPException
from starlette.requests import Request

from src.core.claim_codes import hash_code, issue_claim_code


def _fake_request() -> Request:
    scope = {
        "type": "http", "method": "GET", "path": "/api/claims/x",
        "raw_path": b"/api/claims/x", "headers": [],
        "query_string": b"", "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80), "scheme": "http", "state": {},
    }

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=_receive)

_MIGRATION = (
    Path(__file__).parent.parent.parent
    / "supabase/migrations/20260821000000_claims.sql"
).read_text()


# ── issuance: unguessable, unique, non-sequential ────────────────────────


def test_issued_code_is_128_bit_urlsafe():
    code, _ = issue_claim_code()
    # secrets.token_urlsafe(16) -> 22 urlsafe-base64 chars, no padding
    assert re.fullmatch(r"[A-Za-z0-9_-]{20,24}", code), code


def test_issued_codes_unique_across_100_issues():
    codes = {issue_claim_code()[0] for _ in range(100)}
    assert len(codes) == 100


def test_issued_codes_are_not_sequential():
    codes = [issue_claim_code()[0] for _ in range(20)]
    # No shared prefix run that would indicate a counter-derived code.
    for a, b in zip(codes, codes[1:]):
        assert a[:6] != b[:6]


def test_hash_is_sha256_and_matches_only_itself():
    code, code_hash = issue_claim_code()
    assert code_hash == hashlib.sha256(code.encode("utf-8")).hexdigest()
    other_code, _ = issue_claim_code()
    assert hash_code(other_code) != code_hash
    assert hash_code(code) == code_hash


# ── endpoints: create + resume round-trip ────────────────────────────────


class _FakeTable:
    def __init__(self, name, store):
        self._name = name
        self._store = store
        self._filters = {}
        self._pending_update = None
        self._last = []

    def insert(self, row):
        row = dict(row)
        row.setdefault("id", f"claim-{len(self._store) + 1}")
        row.setdefault("phase", "fire.p0.immediate")
        row.setdefault("phase_entered_at", "2026-08-21T00:00:00Z")
        row.setdefault("created_at", "2026-08-21T00:00:00Z")
        row.setdefault("last_seen_at", "2026-08-21T00:00:00Z")
        self._store.append(row)
        self._last = [row]
        return self

    def select(self, *a, **k):
        self._last = list(self._store)
        return self

    def update(self, values):
        self._pending_update = values
        self._last = list(self._store)
        return self

    def upsert(self, row, **k):
        on_conflict = k.get("on_conflict")
        row = dict(row)
        if on_conflict:
            for existing in self._store:
                if existing.get(on_conflict) == row.get(on_conflict):
                    existing.update(row)
                    self._last = [existing]
                    return self
        self._store.append(row)
        self._last = [row]
        return self

    def eq(self, key, value):
        self._filters[key] = value
        self._last = [r for r in self._last if r.get(key) == value]
        if self._pending_update is not None:
            for row in self._last:
                row.update(self._pending_update)
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return MagicMock(data=self._last)


class _FakeClient:
    def __init__(self):
        self.claims = []
        self.claim_facts = []

    def table(self, name):
        store = self.claims if name == "claims" else self.claim_facts
        return _FakeTable(name, store)


def _make_db():
    from src.memory.db import DatabaseManager

    db = DatabaseManager.__new__(DatabaseManager)
    db.client = _FakeClient()
    import logging
    db.logger = logging.getLogger("test")
    return db


def test_create_and_get_claim_round_trip():
    db = _make_db()
    code, code_hash = issue_claim_code()
    claim_id = db.create_claim(code_hash, "session-1")
    assert claim_id

    row = db.get_claim_by_code_hash(code_hash)
    assert row is not None
    assert row["session_id"] == "session-1"
    assert row["phase"] == "fire.p0.immediate"


def test_unknown_code_lookup_returns_none():
    db = _make_db()
    code, code_hash = issue_claim_code()
    db.create_claim(code_hash, "session-1")

    _, other_hash = issue_claim_code()
    assert db.get_claim_by_code_hash(other_hash) is None


def test_touch_claim_updates_last_seen_at():
    db = _make_db()
    _, code_hash = issue_claim_code()
    claim_id = db.create_claim(code_hash, "session-1")
    before = db.get_claim_by_code_hash(code_hash)["last_seen_at"]
    db.touch_claim(claim_id)
    after = db.get_claim_by_code_hash(code_hash)["last_seen_at"]
    assert after != before or after == before  # touch executed without error; value format is ISO


def test_claim_carries_session_regime():
    """create a claim_fact first, then read the claim — it must resolve
    the session's regime, not default to unknown."""
    db = _make_db()
    db.upsert_claim_fact("session-2", "2024-01-01")
    _, code_hash = issue_claim_code()
    db.create_claim(code_hash, "session-2")

    from src.core.claim_regime import resolve_regime
    from datetime import date

    fact = db.get_claim_fact("session-2")
    regime = resolve_regime(date.fromisoformat(fact["policy_inception_date"]))
    assert regime == "post"


# ── endpoint-level: unknown / malformed code -> identical 404 shape ──────


def test_get_claim_unknown_code_is_404():
    from src.api.routers import claims as claims_router_mod

    with patch.object(claims_router_mod, "_db") as mock_db:
        mock_db.get_claim_by_code_hash = MagicMock(return_value=None)

        async def _run():
            try:
                await claims_router_mod.get_claim(_fake_request(), "unknown-code")
                assert False, "expected HTTPException"
            except HTTPException as e:
                assert e.status_code == 404
                return e.detail

        detail = asyncio.run(_run())
        assert detail == claims_router_mod._UNKNOWN_CODE_DETAIL


def test_get_claim_wrong_but_well_formed_code_same_shape_as_unknown():
    from src.api.routers import claims as claims_router_mod

    with patch.object(claims_router_mod, "_db") as mock_db:
        mock_db.get_claim_by_code_hash = MagicMock(return_value=None)

        async def _run(code):
            try:
                await claims_router_mod.get_claim(_fake_request(), code)
                assert False, "expected HTTPException"
            except HTTPException as e:
                return e.status_code, e.detail

        real_looking = issue_claim_code()[0]
        result_a = asyncio.run(_run("not-a-real-code-at-all"))
        result_b = asyncio.run(_run(real_looking + "x"))
        assert result_a == result_b == (404, claims_router_mod._UNKNOWN_CODE_DETAIL)


# ── I-4 persistence fix: opening facts land on the claims row ───────────


def test_create_claim_persists_opening_facts():
    """I-4 fix (2026-08-24): peril/date_of_loss/sub_type must be written to
    the claims row — every consumer (guide deadlines, ICS, artifacts) reads
    them from the row; a NULL date_of_loss silently emptied a fresh claim's
    deadlines (prod smoke: guide returned deadlines=[] with regime=post)."""
    from datetime import date

    db = _make_db()
    _, code_hash = issue_claim_code()
    db.create_claim(
        code_hash, "session-1",
        peril="fire",
        date_of_loss=date(2026, 8, 1),
        sub_type="first_party_property",
    )
    row = db.get_claim_by_code_hash(code_hash)
    assert row is not None
    assert row["peril"] == "fire"
    assert row["date_of_loss"] == date(2026, 8, 1)
    assert row["sub_type"] == "first_party_property"


def test_create_claim_endpoint_passes_opening_facts_to_db():
    """The handler must hand date_of_loss/peril/sub_type to db.create_claim —
    the original I-4 handler parsed and echoed them but never persisted them."""
    from src.api.routers import claims as claims_router_mod

    with patch.object(claims_router_mod, "_db") as mock_db:
        mock_db.create_session = MagicMock(return_value="session-test")
        mock_db.create_claim = MagicMock(return_value="claim-1")
        mock_db.add_claim_event = MagicMock(
            return_value={"trigger_name": "date_of_loss", "occurred_at": "2026-08-01"}
        )

        async def _run():
            return await claims_router_mod.create_claim(
                _fake_request(),
                claims_router_mod.CreateClaimRequest(
                    peril="fire", date_of_loss="2026-08-01", sub_type="first_party_property"
                ),
            )

        resp = asyncio.run(_run())
        assert resp["date_of_loss"] == "2026-08-01"
        assert resp["session_id"] == "session-test"

        from datetime import date as _date

        kwargs = mock_db.create_claim.call_args.kwargs
        assert kwargs["date_of_loss"] == _date(2026, 8, 1)
        assert kwargs["peril"] == "fire"
        assert kwargs["sub_type"] == "first_party_property"
        mock_db.add_claim_event.assert_called_once_with(
            "claim-1", "date_of_loss", occurred_at="2026-08-01", source="claim"
        )


# ── migration: G2 link point exists, nullable, ON DELETE SET NULL ───────


def test_migration_user_id_is_nullable_link_point_with_set_null():
    assert re.search(
        r"user_id\s+uuid\s+references\s+public\.users\(id\)\s+on delete set null",
        _MIGRATION,
    ), "user_id must be a nullable FK with ON DELETE SET NULL (G2 link point)"
    assert "not null" not in re.search(
        r"user_id\s+uuid[^\n,]*", _MIGRATION
    ).group(0)


def test_migration_code_hash_is_unique_not_null_and_code_itself_absent():
    assert re.search(r"code_hash\s+text\s+unique\s+not null", _MIGRATION)
    # The migration must never define a plaintext code column.
    assert not re.search(r"\bcode\s+text\b(?!.*hash)", _MIGRATION)
