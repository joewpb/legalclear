"""Phase 22 — case-law search repointed to the Supabase legal_opinions
corpus (PRIMARY), with CourtListener an optional v4-token fallback only.

These are FastAPI TestClient unit tests — no running server and no Supabase
creds required. The corpus query is monkeypatched, so the response contract
is verified without any network or DB dependency.

Sanctions guard: every courtlistener_url is either null or a reconstructed
/opinion/<cluster_id>/ URL (a real CourtListener ID captured at ingest) —
never an invented link.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.routes import app
from src.api.routers import case_law

client = TestClient(app)

_FAKE_ROWS = [
    {
        "case_name": "State v. Example",
        "citation": "123 So. 3d 1 (Fla. 2010)",
        "court": "Supreme Court of Florida",
        "date_filed": "2010-05-01",
        "cluster_id": 999,
        "summary_plain": "A DUI checkpoint case.",
    },
    {
        "case_name": "Anon v. City of X",
        "citation": "",
        "court": "District Court of Appeal of Florida",
        "date_filed": "2012-03-04",
        "cluster_id": None,
        "summary_plain": "An opinion with no cluster_id and no citation.",
    },
]


def test_search_returns_corpus_results(monkeypatch):
    """Supabase-primary path: 200 with corpus-shaped results."""
    monkeypatch.setattr(
        case_law,
        "_search_opinions_corpus",
        lambda q, c, limit=10: list(_FAKE_ROWS),
    )
    r = client.post(
        "/api/case-law/search",
        json={"query": "DUI", "court_filter": "all"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "DUI"
    assert len(data["results"]) == 2

    for res in data["results"]:
        # required contract fields, all sourced from rows
        assert res["case_name"]
        assert "citation" in res
        assert res["plain_english_summary"] is not None
        # URL reconstructed from cluster_id only — never fabricated
        if res["courtlistener_url"] is not None:
            assert res["courtlistener_url"].startswith(
                "https://www.courtlistener.com/opinion/"
            ), f"Fabricated URL detected: {res['courtlistener_url']}"

    # one row has cluster_id (URL), one does not (null)
    urls = [res["courtlistener_url"] for res in data["results"]]
    assert any(u is not None for u in urls)
    assert any(u is None for u in urls)


def test_no_fabricated_results_on_empty_corpus(monkeypatch):
    """Empty corpus + no CL token -> 200 with empty results (never invented)."""
    monkeypatch.setattr(
        case_law, "_search_opinions_corpus", lambda q, c, limit=10: []
    )
    monkeypatch.setattr(
        case_law, "_courtlistener_v4_fallback", lambda q, c: []
    )
    r = client.post(
        "/api/case-law/search",
        json={"query": "zxcvbnm impossible nonsense 99999", "court_filter": "all"},
    )
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_court_filter_handled(monkeypatch):
    """Every court filter returns 200 (no CourtListener 502)."""
    monkeypatch.setattr(
        case_law,
        "_search_opinions_corpus",
        lambda q, c, limit=10: list(_FAKE_ROWS),
    )
    for f in ("all", "fl_supreme", "fl_appellate", "federal_fl"):
        r = client.post(
            "/api/case-law/search",
            json={"query": "negligence", "court_filter": f},
        )
        assert r.status_code == 200, f"court_filter={f} failed"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
