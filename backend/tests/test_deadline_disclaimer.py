"""B4b-2 — deadline.py disclaimer regression tests.

Pins that every disclaimer-bearing response path in
src/api/routers/deadline.py sources its disclaimer from
core.upl.apply_disclaimer (not a local/duplicated string), and that the
router's own source contains no hardcoded external-link literals.

Response-level link-freeness is NOT asserted here: on this branch,
apply_disclaimer's own text still contains links (that strip lands in
B4b-1). Once B4b-1 merges, the equality assertions below make
link-freeness true automatically without touching this file.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("API_KEY", "testkey123")

from fastapi.testclient import TestClient

from src.api.routers import deadline as deadline_router
from src.api.routes import app
from src.core.config import settings
from src.core.upl import apply_disclaimer

client = TestClient(app)

DOCUMENT_ID = "doc-1"
OWNING_SESSION = "session-owner"


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


def test_get_deadlines_disclaimer_matches_canonical(monkeypatch):
    rows = [{"id": "dl-1", "label": "Answer"}]
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=rows))
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/deadlines",
        params={"session_id": OWNING_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    body = r.json()
    expected = apply_disclaimer({"deadlines": rows}, lang="en")
    assert body["disclaimer"] == expected["disclaimer"]


def test_get_trigger_events_disclaimer_matches_canonical(monkeypatch):
    rows = [{"id": "te-1"}]
    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=rows))
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/trigger-events",
        params={"session_id": OWNING_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 200
    body = r.json()
    expected = apply_disclaimer({"trigger_events": rows}, lang="en")
    assert body["disclaimer"] == expected["disclaimer"]


def test_analyze_disclaimer_matches_canonical(monkeypatch):
    pipeline_result = {"document_id": DOCUMENT_ID, "deadlines": [], "trigger_events": []}

    async def _fake_run_pipeline(document_id, text, db):
        return pipeline_result

    monkeypatch.setattr(deadline_router, "db", _FakeDB(rows=[]))
    monkeypatch.setattr(deadline_router.db, "get_document",
                         lambda doc_id: {"id": doc_id, "document_text": "some text"})

    import deadline.pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "run_deadline_pipeline", _fake_run_pipeline)

    r = client.post(
        f"/api/deadline/analyze/{DOCUMENT_ID}",
        headers={"x-api-key": settings.API_KEY},
    )
    assert r.status_code == 200
    body = r.json()
    expected = apply_disclaimer(pipeline_result, lang="en")
    assert body["disclaimer"] == expected["disclaimer"]


def test_get_deadlines_error_path_has_no_disclaimer(monkeypatch):
    """Documents current behavior: the 500 error path raises HTTPException
    with a plain `detail` string and carries no disclaimer at all.

    This is a FINDING, not a fix — B4b-2 is tests-only, no behavioral
    changes. If a future phase adds a disclaimer to error responses, this
    test should be updated to assert equality with apply_disclaimer instead
    of asserting its absence.
    """

    class _BoomQuery(_FakeQuery):
        def execute(self):
            raise RuntimeError("boom")

    class _BoomClient(_FakeClient):
        def table(self, name):
            return _BoomQuery(self._rows)

    class _BoomDB(_FakeDB):
        def __init__(self):
            super().__init__(rows=[])
            self.client = _BoomClient(rows=[])

    monkeypatch.setattr(deadline_router, "db", _BoomDB())
    r = client.get(
        f"/api/deadline/{DOCUMENT_ID}/deadlines",
        params={"session_id": OWNING_SESSION},
        headers={"x-api-key": "testkey123"},
    )
    assert r.status_code == 500
    body = r.json()
    assert "disclaimer" not in body


def test_deadline_router_source_has_no_hardcoded_external_links():
    """The router's own string literals must not hardcode florida law-help
    links — any disclaimer/link text must flow through apply_disclaimer
    (core/upl.py), not be duplicated here.
    """
    source = inspect.getsource(deadline_router)
    forbidden = ["floridalawhelp", "floridabar", "http://", "https://"]
    for token in forbidden:
        assert token not in source, f"found forbidden literal {token!r} in deadline.py"
