"""FL Case Law Lookup router — repointed to the Supabase legal_opinions
corpus (759 high-citation FL opinions) as PRIMARY source.

Previously every search proxied to CourtListener REST v3, which 403s
unauthenticated requests and is deprecated. We own the corpus, so search
runs against it directly via ILIKE over the scalar text columns.
CourtListener is kept ONLY as an optional v4 fallback, gated on
COURTLISTENER_TOKEN — with no token (default) CL is gone entirely.

Sanctions-protection invariants preserved (see Mata v. Avianca, 2023):
  1. case_name / citation / court / date_filed / plain_english_summary
     come ONLY from corpus rows — nothing is invented.
  2. courtlistener_url is RECONSTRUCTED from the row's cluster_id (a real
     CourtListener ID captured at ingest) → /opinion/<cluster_id>/, or
     null when cluster_id is absent. Never fabricated.
  3. No LLM writes anything. The v3 snippet-summarizer is removed;
     summary_plain maps straight through to plain_english_summary.

Limitation: key_statutes and parties are text[] arrays and cannot be
ILIKE-searched via PostgREST, so free-text search covers the five scalar
columns only (case_name, summary_plain, summary_legal, legal_issue,
core_facts). Party names and statute refs typically appear in those.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from src.core.config import settings
from src.core.upl import apply_disclaimer
from src.memory.db import DatabaseManager

router = APIRouter(prefix="/api/case-law")
logger = logging.getLogger(__name__)

db = DatabaseManager()

# Scalar text columns searched by ILIKE for a free-text query. The corpus's
# key_statutes / parties columns are text[] arrays (incompatible with ILIKE).
_SEARCH_COLUMNS = (
    "case_name",
    "summary_plain",
    "summary_legal",
    "legal_issue",
    "core_facts",
)

# Columns selected from legal_opinions for the response. cluster_id drives
# the URL reconstruction; we still rank by cite_count without selecting it.
_SELECT_COLUMNS = "case_name, citation, court, date_filed, cluster_id, summary_plain"

# Court filter → ILIKE pattern on the corpus `court` column. The corpus
# holds only the two Florida state appellate courts (no federal rows were
# ingested), so federal_fl matches nothing.
_COURT_FILTER: dict[str, Optional[str]] = {
    "fl_supreme": "Supreme Court of Florida",
    "fl_appellate": "District Court of Appeal of Florida",
    "federal_fl": None,  # no federal opinions in the corpus
    "all": None,
}

_CL_BASE = "https://www.courtlistener.com"
_CL_V4_SEARCH = "https://www.courtlistener.com/api/rest/v4/search/"
_RESULT_LIMIT = 10

# Strip chars that would break a PostgREST `or`/`ilike` filter value or let
# a user term escape the predicate (commas separate predicates, parens
# group, colons split col.op.value, * is a wildcard).
_TERM_SCRUB = re.compile(r"[,():*]")


class CaseLawSearchRequest(BaseModel):
    query: str
    court_filter: str = "all"


def _sanitize_term(term: str) -> str:
    return _TERM_SCRUB.sub(" ", term).strip()


def _build_or_filter(term: str) -> str:
    """PostgREST `or=` filter across the searchable text columns."""
    t = _sanitize_term(term)
    if not t:
        return ""
    frag = f"%{t}%"
    return ",".join(f"{c}.ilike.{frag}" for c in _SEARCH_COLUMNS)


def _search_opinions_corpus(
    query: str, court_filter: str, limit: int = _RESULT_LIMIT
) -> list[dict]:
    """ILIKE-search the legal_opinions corpus. Returns [] on no creds, no
    query, or query error — retrieval never breaks the parent response."""
    if db.client is None:
        return []
    or_filter = _build_or_filter(query)
    if not or_filter:
        return []
    try:
        req = (
            db.client.table("legal_opinions")
            .select(_SELECT_COLUMNS)
            .or_(or_filter)
            .eq("quality_flagged", False)
        )
        court_value = _COURT_FILTER.get(court_filter)
        if court_value:
            req = req.ilike("court", f"%{court_value}%")
        result = req.order("cite_count", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:  # noqa: BLE001 — fail-soft, never break response
        logger.error("legal_opinions ILIKE search failed: %s", e)
        return []


def _courtlistener_v4_fallback(
    query: str, court_filter: str  # noqa: ARG001 — court_filter reserved for future v4 mapping
) -> list[dict]:
    """Optional CourtListener v4 fallback. Runs ONLY when a
    COURTLISTENER_TOKEN is configured AND the corpus returned nothing.
    OFF by default; untested (CL v3 was 403'ing us). Returns [] on any
    failure so the response degrades to corpus-only, never errors."""
    token = getattr(settings, "COURTLISTENER_TOKEN", "") or ""
    if not token:
        return []
    try:
        with httpx.Client(timeout=15.0) as http:
            r = http.get(
                _CL_V4_SEARCH,
                params={"q": query, "type": "o"},
                headers={"Authorization": f"Token {token}"},
            )
            r.raise_for_status()
        out: list[dict] = []
        for row in (r.json().get("results") or [])[:_RESULT_LIMIT]:
            abs_url = row.get("absolute_url")
            if not abs_url:
                continue  # HARD RULE: never fabricate a URL
            url = (
                abs_url
                if abs_url.startswith(_CL_BASE)
                else f"{_CL_BASE}{abs_url}"
            )
            out.append(
                {
                    "case_name": row.get("caseName", "Unknown case name"),
                    "citation": row.get("citation") or "",
                    "court": row.get("court") or "",
                    "date_filed": row.get("dateFiled") or "",
                    "cluster_id": None,
                    "summary_plain": None,
                    # Surface the real CL URL captured from absolute_url —
                    # _row_to_result prefers this over the (null) cluster_id
                    # reconstruction so the fallback row keeps its link.
                    "url": url,
                }
            )
        return out
    except Exception as e:  # noqa: BLE001 — graceful degradation
        logger.warning(
            "CourtListener v4 fallback failed (%s); corpus-only",
            type(e).__name__,
        )
        return []


def _row_to_result(row: dict) -> dict:
    """Map a corpus/CL row to the CaseResult contract. URL reconstructed
    from cluster_id (a real CourtListener ID); null when absent.

    A row may carry an explicit ``url`` — the CL v4 fallback captures the
    opinion's real ``absolute_url`` directly (cluster_id is unknown in that
    path). When present it is preferred over the cluster_id reconstruction
    so the fallback row keeps its link instead of degrading to null."""
    explicit_url = row.get("url")
    if explicit_url:
        courtlistener_url = explicit_url
    else:
        cluster_id = row.get("cluster_id")
        courtlistener_url = (
            f"{_CL_BASE}/opinion/{cluster_id}/" if cluster_id else None
        )
    return {
        "case_name": row.get("case_name") or "Unknown case name",
        "citation": row.get("citation") or "",
        "court": row.get("court") or "Unknown court",
        "date_filed": row.get("date_filed") or "",
        "plain_english_summary": row.get("summary_plain") or None,
        "courtlistener_url": courtlistener_url,
    }


@router.post("/search")
async def search_case_law(req: CaseLawSearchRequest):
    """Search the FL case-law corpus (Supabase legal_opinions) by free text.

    Hard rules enforced here:
      1. case_name / citation / court / date_filed / plain_english_summary
         come ONLY from corpus rows.
      2. courtlistener_url is reconstructed from the stored cluster_id (a
         real CourtListener ID) or null — never invented.
      3. No LLM is invoked; the v3 snippet-summarizer is gone.
    Supabase I/O is synchronous (supabase-py), so it is offloaded to a
    thread to avoid blocking the event loop and every other SSE client.
    """
    rows = await asyncio.to_thread(
        _search_opinions_corpus, req.query, req.court_filter, _RESULT_LIMIT
    )
    if not rows and getattr(settings, "COURTLISTENER_TOKEN", ""):
        rows = await asyncio.to_thread(
            _courtlistener_v4_fallback, req.query, req.court_filter
        )

    results = [_row_to_result(r) for r in rows]
    return apply_disclaimer(
        {
            "results": results,
            "total_results": len(results),
            "query": req.query,
        },
        lang="en",
    )
