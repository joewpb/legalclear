# PHASE 22 — FL Case Law Lookup (CourtListener)
**Status: BUILD. Prerequisite: Phases 15–21 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.
- **No `myflcourtaccess.com` automation.**

## Critical phase-specific rule

**The LLM is FORBIDDEN from generating case names, citations, or court fields.** These come ONLY from the CourtListener API. The LLM may only write a 2-sentence plain-English summary of the returned snippet. Any result missing a CourtListener URL must be dropped before returning.

This is the sanctions-protection layer. Lawyers have been disbarred for citing fake cases (Mata v. Avianca, 2023). The architecture below makes hallucination structurally impossible.

## Universal DO-NOT-TOUCH

- Existing agents
- Stripe paywall
- `.env`, env vars
- Existing FastAPI routes
- No new npm packages
- Python: install `httpx` only if missing — `uv add httpx`

## Goal

Search FL case law via CourtListener public API. RAG-only architecture. LLM enriches with plain-English summary; never invents cites. Court filter for FL Supreme / FL Appellate / Federal applying FL law / All.

## Frontend deliverables

### Create
```
frontend/src/pages/CaseLawLookupFL.tsx
frontend/src/components/caselaw/SearchBar.tsx
frontend/src/components/caselaw/CourtFilter.tsx
frontend/src/components/caselaw/ResultsList.tsx
frontend/src/components/caselaw/ResultCard.tsx
```

### Modify
- Frontend router: route `/case-law` → `CaseLawLookupFL`.

## UI spec

- **Search text input** (large, mono, Brutalist style)
- **Court filter dropdown:** All / FL Supreme / FL Appellate / Federal applying FL law
- **SEARCH button** → POST `/api/case-law/search`
- **Disclaimer above results** (always visible): "Results from CourtListener public database. Always verify by reading the full opinion."
- **Result cards:**
  - Case name (mono, large, top of card)
  - Citation (mono, muted, below case name)
  - Court + date filed (small, sans, right side)
  - Plain-English summary (sans, 2 sentences) — may be empty if LLM call failed
  - "VIEW ON COURTLISTENER" link (button style, opens in new tab)
- **Empty state:** "No matches in CourtListener for that query. Try different keywords or broaden your court filter."

## Backend deliverables

### Install `httpx` if missing
```bash
cd backend && uv add httpx
```

### Create `backend/src/api/routes/case_law.py`

```python
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic

router = APIRouter(prefix="/api/case-law")
client = Anthropic()

COURT_MAP = {
    "fl_supreme": "fla",
    "fl_appellate": "flaapp",
    "federal_fl": "flmd,flnd,flsd,ca11",
    "all": None,
}

class CaseLawSearchRequest(BaseModel):
    query: str
    court_filter: str = "all"

@router.post("/search")
async def search_case_law(req: CaseLawSearchRequest):
    """
    CRITICAL RULES enforced by this endpoint:
    1. NEVER generate case_name, citation, or court fields. Only CourtListener supplies these.
    2. Drop any result without an absolute_url from CourtListener.
    3. LLM only summarizes the snippet — never invents cases.
    """
    params = {"q": req.query, "type": "o"}
    if req.court_filter != "all" and req.court_filter in COURT_MAP:
        mapped = COURT_MAP[req.court_filter]
        if mapped:
            params["court"] = mapped

    async with httpx.AsyncClient() as http:
        try:
            cl = await http.get(
                "https://www.courtlistener.com/api/rest/v3/search/",
                params=params,
                timeout=15.0
            )
            cl.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"CourtListener unavailable: {e}")

    cl_data = cl.json()
    raw_results = cl_data.get("results", [])[:10]

    enriched = []
    for r in raw_results:
        absolute_url = r.get("absolute_url")
        if not absolute_url:
            # HARD RULE: skip any result without a CourtListener URL
            continue

        cl_full_url = f"https://www.courtlistener.com{absolute_url}"
        snippet = r.get("snippet", "")

        # LLM summary — OPTIONAL, summary only, NEVER touches case_name/citation/court
        summary = None
        if snippet:
            try:
                msg = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=200,
                    system=[{
                        "type": "text",
                        "text": "You write 2-sentence plain-English summaries of legal opinion snippets. Do NOT invent case names, citations, or court information.",
                        "cache_control": {"type": "ephemeral"}
                    }],
                    messages=[{
                        "role": "user",
                        "content": f"Summarize this opinion snippet in 2 plain-English sentences for a non-lawyer: {snippet}"
                    }]
                )
                summary = msg.content[0].text.strip()
            except Exception:
                summary = None  # graceful fallback — result still returned without summary

        enriched.append({
            "case_name": r.get("caseName", "Unknown case name"),
            "citation": r.get("citation", [""])[0] if r.get("citation") else "",
            "court": r.get("court", "Unknown court"),
            "date_filed": r.get("dateFiled", ""),
            "plain_english_summary": summary,
            "courtlistener_url": cl_full_url
        })

    return {
        "results": enriched,
        "total_results": cl_data.get("count", 0),
        "query": req.query
    }
```

### Register router
```python
from .routes.case_law import router as case_law_router
app.include_router(case_law_router)
```

## Verification — `backend/tests/test_phase_22.py`

```python
import httpx

BACKEND = "http://localhost:8001"

def test_search_returns_real_courtlistener_results():
    r = httpx.post(f"{BACKEND}/api/case-law/search", json={
        "query": "stand your ground self defense",
        "court_filter": "fl_supreme"
    }, timeout=30.0)
    assert r.status_code in (200, 502)  # 502 acceptable if CourtListener temporarily unavailable
    if r.status_code == 200:
        data = r.json()
        assert "results" in data
        # HARD CHECK: every result MUST have a courtlistener_url
        for result in data["results"]:
            assert "courtlistener_url" in result
            assert result["courtlistener_url"].startswith("https://www.courtlistener.com"), \
                f"Fabricated URL detected: {result['courtlistener_url']}"

def test_no_fabricated_results_on_empty_query():
    """Even on nonsense query, response must have empty array — not LLM-invented cases."""
    r = httpx.post(f"{BACKEND}/api/case-law/search", json={
        "query": "zxcvbnm impossible nonsense query string 99999",
        "court_filter": "all"
    }, timeout=30.0)
    if r.status_code == 200:
        data = r.json()
        # All returned results must still have valid CourtListener URLs
        for result in data["results"]:
            assert result["courtlistener_url"].startswith("https://www.courtlistener.com")

def test_court_filter_handled():
    """Court filter doesn't break the endpoint."""
    for f in ["all", "fl_supreme", "fl_appellate", "federal_fl"]:
        r = httpx.post(f"{BACKEND}/api/case-law/search", json={
            "query": "negligence",
            "court_filter": f
        }, timeout=30.0)
        assert r.status_code in (200, 502)

if __name__ == "__main__":
    test_search_returns_real_courtlistener_results()
    test_no_fabricated_results_on_empty_query()
    test_court_filter_handled()
    print("PHASE 22 COMPLETE — all checks passed.")
```

## Pass criteria

- Search input + court filter render
- POST hits CourtListener real API
- Every displayed result has `courtlistener_url` starting with `https://www.courtlistener.com`
- Results without `absolute_url` from CourtListener are DROPPED, not invented
- LLM summary appears when CourtListener returns a snippet; null when it doesn't
- LLM call uses `cache_control: ephemeral`
- LLM never modifies `case_name`, `citation`, `court`, `date_filed`, or `courtlistener_url` fields
- Disclaimer renders above results
- Empty state message appears when no results
- `test_phase_22.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 22 BLOCKED — [error]` and STOP.

If any fabricated URL is detected (a result with a URL that doesn't start with `https://www.courtlistener.com`), STOP IMMEDIATELY and report. That's a critical safety failure.

## Final report

```
PHASE 22 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 23 — the final phase.
