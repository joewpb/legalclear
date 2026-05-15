"""Phase 22 verification — copied verbatim from
phases/source/PHASE_22_case_law.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
  - Network egress to CourtListener (test tolerates 502 if it's down).

The critical check is structural: every returned result MUST have a URL
that starts with `https://www.courtlistener.com`. The router drops any
CourtListener row without `absolute_url`, so a fabricated URL leaking
through would be a sanctions-class regression — not just a test failure.
"""
import httpx

BACKEND = "http://localhost:8001"


def test_search_returns_real_courtlistener_results():
    r = httpx.post(
        f"{BACKEND}/api/case-law/search",
        json={"query": "stand your ground self defense", "court_filter": "fl_supreme"},
        timeout=30.0,
    )
    assert r.status_code in (200, 502)  # 502 acceptable if CourtListener temporarily unavailable
    if r.status_code == 200:
        data = r.json()
        assert "results" in data
        # HARD CHECK: every result MUST have a courtlistener_url
        for result in data["results"]:
            assert "courtlistener_url" in result
            assert result["courtlistener_url"].startswith(
                "https://www.courtlistener.com"
            ), f"Fabricated URL detected: {result['courtlistener_url']}"


def test_no_fabricated_results_on_empty_query():
    """Even on nonsense query, response must have empty array — not LLM-invented cases."""
    r = httpx.post(
        f"{BACKEND}/api/case-law/search",
        json={
            "query": "zxcvbnm impossible nonsense query string 99999",
            "court_filter": "all",
        },
        timeout=30.0,
    )
    if r.status_code == 200:
        data = r.json()
        # All returned results must still have valid CourtListener URLs
        for result in data["results"]:
            assert result["courtlistener_url"].startswith(
                "https://www.courtlistener.com"
            )


def test_court_filter_handled():
    """Court filter doesn't break the endpoint."""
    for f in ["all", "fl_supreme", "fl_appellate", "federal_fl"]:
        r = httpx.post(
            f"{BACKEND}/api/case-law/search",
            json={"query": "negligence", "court_filter": f},
            timeout=30.0,
        )
        assert r.status_code in (200, 502)


if __name__ == "__main__":
    test_search_returns_real_courtlistener_results()
    test_no_fabricated_results_on_empty_query()
    test_court_filter_handled()
    print("PHASE 22 COMPLETE — all checks passed.")
