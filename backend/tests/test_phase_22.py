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


# ---------------------------------------------------------------------------
# CL v4 fallback URL surfacing. Regression for the compute-then-discard bug
# where _courtlistener_v4_fallback() built a real URL from absolute_url but
# never included it in the output dict, and set cluster_id=None so
# _row_to_result() reconstructed courtlistener_url as null too — every
# fallback row lost its CourtListener link. Pure unit tests, no network.
# ---------------------------------------------------------------------------


def test_row_to_result_url_precedence():
    """_row_to_result prefers an explicit url; falls back to cluster_id;
    null when neither is present."""
    # Explicit url wins over cluster_id.
    row = {
        "case_name": "X",
        "cluster_id": 999,
        "url": "https://www.courtlistener.com/opinion/42/x-v-y/",
    }
    assert case_law._row_to_result(row)["courtlistener_url"] == (
        "https://www.courtlistener.com/opinion/42/x-v-y/"
    )
    # No explicit url -> cluster_id reconstruction (corpus behavior unchanged).
    assert case_law._row_to_result({"case_name": "Y", "cluster_id": 999})[
        "courtlistener_url"
    ] == "https://www.courtlistener.com/opinion/999/"
    # Neither -> null.
    assert case_law._row_to_result({"case_name": "Z", "cluster_id": None})[
        "courtlistener_url"
    ] is None


class _FakeCLResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):  # noqa: ANN201
        pass

    def json(self):  # noqa: ANN201
        return self._payload


class _FakeCLClient:
    """Stand-in for httpx.Client — returns a canned CourtListener v4 payload.

    Two rows: one with a real absolute_url (must surface), one without
    (must be dropped — HARD RULE: never fabricate a URL)."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):  # noqa: ANN001, ANN201
        return _FakeCLResponse(
            {
                "results": [
                    {
                        "caseName": "Smith v. State",
                        "citation": "456 So. 3d 2 (Fla. 2011)",
                        "court": "District Court of Appeal of Florida",
                        "dateFiled": "2011-06-15",
                        "absolute_url": "/opinion/987654/smith-v-state/",
                    },
                    {
                        # No absolute_url -> skipped, never fabricated.
                        "caseName": "Ghost v. Nobody",
                        "absolute_url": None,
                    },
                ]
            }
        )


def test_cl_v4_fallback_surfaces_real_url(monkeypatch):
    """The CL v4 fallback must carry the opinion's real absolute_url through
    as `url`, and _row_to_result must surface it as courtlistener_url (not
    null). Before the fix, every fallback row lost its link."""
    monkeypatch.setattr(case_law.httpx, "Client", _FakeCLClient)
    monkeypatch.setattr(case_law.settings, "COURTLISTENER_TOKEN", "test-token")

    rows = case_law._courtlistener_v4_fallback("DUI", "all")
    # The no-abs_url row is dropped; only the real one survives.
    assert len(rows) == 1
    row = rows[0]
    assert row["url"] == (
        "https://www.courtlistener.com/opinion/987654/smith-v-state/"
    )
    # Surfaced through the contract, and passes the sanctions guard.
    result = case_law._row_to_result(row)
    assert result["courtlistener_url"] == row["url"]
    assert result["courtlistener_url"].startswith(
        "https://www.courtlistener.com/opinion/"
    )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
