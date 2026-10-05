"""FL Case Law Lookup router — deterministic full-corpus search.

Search pipeline (no LLM anywhere, no external API in the hot path):

  1. Name detection: a query containing a "v." / "vs." party separator is a
     case-name lookup — `case_name ILIKE %<query>%` first (trgm-indexed).
  2. Term search: the query is tokenized into search terms (spaces AND
     hyphens both split), stopwords dropped, scrub-safe; each term is an
     OR'd ILIKE predicate on summary_plain. Candidates are fetched
     cite_count-desc (the DB narrows, Python ranks).
  3. Relevance ranking in Python (deterministic): distinct matched terms
     DESC, then cite_count DESC, then cluster_id DESC (stable tiebreak).
     Rows must match >= 1 term. Junk rows (empty case_name, empty/tiny
     summary_plain) are dropped before ranking.
  4. Honest totals: total_results == shipped rows, always.

CourtListener is kept ONLY as an optional fallback gated on
COURTLISTENER_TOKEN (default OFF) for when the corpus has nothing.

Sanctions-protection invariants preserved (Mata v. Avianca, 2023):
  - case_name / citation / court / date_filed / plain_english_summary come
    ONLY from corpus rows — nothing is invented.
  - courtlistener_url is reconstructed from the stored cluster_id (a real
    CourtListener ID) or null — never fabricated.
  - No LLM writes anything.
"""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.api.limiter import limiter
from src.core.config import settings
from src.core.upl import apply_disclaimer
from src.memory.db import DatabaseManager

router = APIRouter(prefix="/api/case-law")
logger = logging.getLogger(__name__)

db = DatabaseManager()

# Scalar text columns searched by ILIKE for a free-text query.
_SEARCH_COLUMNS = (
    "summary_plain",
)

# Columns selected from legal_opinions for the response.
_SELECT_COLUMNS = "case_name, citation, court, date_filed, cluster_id, summary_plain, cite_count"

# Court filter → ILIKE pattern on the corpus `court` column.
_COURT_FILTER: dict[str, str | None] = {
    "fl_supreme": "Supreme Court of Florida",
    "fl_appellate": "District Court of Appeal",
    "federal_fl": None,  # no federal opinions in the corpus
    "all": None,
}

_CL_BASE = "https://www.courtlistener.com"
_CL_V4_SEARCH = "https://www.courtlistener.com/api/rest/v4/search/"
_RESULT_LIMIT = 10
_CANDIDATE_LIMIT = 200
_MAX_TERMS = 8

# Strip chars that would break a PostgREST `or`/`ilike` filter value or let
# a user term escape the predicate. LIKE wildcards % and _ are scrubbed too.
_TERM_SCRUB = re.compile(r"[,():*%_\\]+")

# Control characters must never reach the wire inside strings.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# Stopwords for keyword-list queries (the shipped chips are keyword lists).
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with",
        "at", "by", "from", "is", "are", "was", "were", "be", "been", "being",
        "my", "me", "i", "we", "you", "your", "he", "she", "it", "its", "his",
        "her", "they", "their", "this", "that", "these", "those", "as", "vs",
        "about", "into", "over", "under", "after", "before", "between", "out",
        "up", "down", "do", "does", "did", "not", "no", "if", "then", "than",
        "so", "but", "how", "what", "when", "where", "who", "why", "which",
    }
)

# A query with a party separator ("v." / "vs." / bare " v ") is a
# case-name lookup.
_NAME_QUERY_RE = re.compile(r"\bv(?:s)?\.?\s+\w", re.IGNORECASE)

# Junk summary: rows whose summary is empty or near-empty carry no content
# worth ranking or showing.
_MIN_SUMMARY_LEN = 100

_CITATION_PLACEHOLDERS: frozenset[str] = frozenset(
    {"n/a", "na", "null", "none", "unknown", "tbd", "pending", "not cited"}
)


class CaseLawSearchRequest(BaseModel):
    query: str
    court_filter: str = "all"


def _scrub(value: str | None) -> str | None:
    """Remove control characters; None-safe."""
    if value is None:
        return None
    return _CONTROL_CHARS.sub(" ", value)


def _sanitize_term(term: str) -> str:
    return _TERM_SCRUB.sub(" ", term).strip()


def _normalize(query: str) -> str:
    """NFKC-normalize so curly quotes/dashes don't defeat matching."""
    return unicodedata.normalize("NFKC", query or "").strip()


def _tokenize(query: str) -> list[str]:
    """Keyword tokens from the query. Hyphens split (self-defense → self,
    defense) — a summary containing "self-defense" also contains "self" and
    "defense" as substrings, so space/hyphen forms match the same content."""
    normalized = _normalize(query).casefold()
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in re.split(r"[^a-z0-9]+", normalized):
        term = _sanitize_term(raw)
        if not term:
            continue
        if len(term) < 2:
            continue
        if term in _STOPWORDS:
            continue
        if term not in seen:
            seen.add(term)
            tokens.append(term)
    return tokens[:_MAX_TERMS]


def _is_name_query(query: str) -> bool:
    """True when the query looks like a case name (has a v./vs. separator)."""
    return bool(_NAME_QUERY_RE.search(_normalize(query)))


def _build_or_filter(terms: list[str]) -> str:
    """PostgREST `or=` filter: each term OR'd across summary_plain."""
    parts = []
    for t in terms:
        clean = _sanitize_term(t)
        if not clean:
            continue
        parts.append(f"summary_plain.ilike.%{clean}%")
    return ",".join(parts)


def _has_case_name(row: dict) -> bool:
    name = row.get("case_name")
    return bool(isinstance(name, str) and name.strip())


def _has_usable_summary(row: dict) -> bool:
    summary = row.get("summary_plain")
    return bool(
        isinstance(summary, str)
        and len(summary.strip()) >= _MIN_SUMMARY_LEN
    )


def _display_citation(row: dict) -> str:
    """Honest citation: '' and placeholders become 'Not available'."""
    citation = (row.get("citation") or "").strip()
    if not citation or citation.casefold() in _CITATION_PLACEHOLDERS:
        return "Not available"
    return citation


def _count_matched_terms(row: dict, terms: list[str]) -> int:
    text = " ".join(
        str(row.get(k) or "") for k in ("summary_plain", "case_name")
    ).casefold()
    return sum(1 for t in terms if t in text)


def _rank(rows: list[dict], terms: list[str]) -> list[dict]:
    """Deterministic ranking: matched terms DESC, cite_count DESC,
    cluster_id DESC (stable tiebreak)."""
    for row in rows:
        row["_matched"] = _count_matched_terms(row, terms)
        row["_cite_count"] = row.get("cite_count") or 0
        row["_cluster_id"] = row.get("cluster_id") or 0
    rows = [r for r in rows if r["_matched"] >= 1]
    rows.sort(
        key=lambda r: (r["_matched"], r["_cite_count"], r["_cluster_id"]),
        reverse=True,
    )
    return rows


def _apply_court_filter(req, court_filter: str):
    court_value = _COURT_FILTER.get(court_filter)
    if court_value:
        return req.ilike("court", f"%{court_value}%")
    return req


def _search_opinions_corpus(query: str, court_filter: str, limit: int) -> list[dict]:
    """Tokenized term search across the corpus (name kept for the Phase 22
    monkeypatch contract). Returns [] on any failure — retrieval never
    breaks the parent response."""
    if db.client is None:
        return []
    terms = _tokenize(query)
    if not terms:
        return []
    or_filter = _build_or_filter(terms)
    if not or_filter:
        return []
    try:
        req = (
            db.client.table("legal_opinions")
            .select(_SELECT_COLUMNS)
            .or_(or_filter)
            .eq("quality_flagged", False)
        )
        req = _apply_court_filter(req, court_filter)
        result = (
            req.order("cite_count", desc=True)
            .order("cluster_id", desc=True)
            .limit(_CANDIDATE_LIMIT)
            .execute()
        )
        rows = []
        for row in result.data or []:
            if not _has_case_name(row) or not _has_usable_summary(row):
                continue
            rows.append(row)
        return _rank(rows, terms)[:limit]
    except Exception as e:
        logger.error("legal_opinions term search failed: %s", e)
        return []


def _search_case_name(query: str, court_filter: str, limit: int) -> list[dict]:
    """Case-name lookup: ILIKE on case_name (trgm-indexed)."""
    if db.client is None:
        return []
    clean = _sanitize_term(_normalize(query))
    if not clean:
        return []
    try:
        req = (
            db.client.table("legal_opinions")
            .select(_SELECT_COLUMNS)
            .ilike("case_name", f"%{clean}%")
            .eq("quality_flagged", False)
        )
        req = _apply_court_filter(req, court_filter)
        result = (
            req.order("cite_count", desc=True)
            .order("cluster_id", desc=True)
            .limit(limit)
            .execute()
        )
        return [r for r in (result.data or []) if _has_case_name(r)]
    except Exception as e:
        logger.error("legal_opinions name search failed: %s", e)
        return []


def _courtlistener_v4_fallback(query: str, court_filter: str) -> list[dict]:
    """Optional CourtListener v4 fallback. Runs ONLY when a
    COURTLISTENER_TOKEN is configured AND the corpus returned nothing.
    OFF by default. Returns [] on any failure."""
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
    except Exception as e:
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
    treatment = row.get("_treatment")
    return {
        "case_name": row.get("case_name") or "Unknown case name",
        "citation": _display_citation(row),
        "court": row.get("court") or "Unknown court",
        "date_filed": row.get("date_filed") or "",
        "cite_count": row.get("cite_count") or 0,
        "plain_english_summary": _scrub(row.get("summary_plain")),
        "courtlistener_url": courtlistener_url,
        # null — never the string "None" (prod bug: untreated rows shipped
        # the literal string "None").
        "citation_treatment": treatment if treatment else None,
    }


def _fetch_treatments(cluster_ids: list[int]) -> dict[int, list[dict]]:
    """Fetch citation treatment records for a batch of cluster IDs.

    Returns {cluster_id: [treatment records]}; {} on error — treatment is
    supplementary, never a hard failure."""
    if not cluster_ids or db.client is None:
        return {}
    try:
        result = (
            db.client.table("citation_treatment")
            .select("cluster_id, treatment_type, treatment_text")
            .in_("cluster_id", cluster_ids)
            .execute()
        )
        out: dict[int, list[dict]] = {}
        for row in result.data or []:
            cid = row["cluster_id"]
            out.setdefault(cid, []).append(
                {"type": row["treatment_type"], "text": row["treatment_text"]}
            )
        return out
    except Exception:
        logger.warning("citation_treatment fetch failed", exc_info=True)
        return {}


@router.post("/search")
@limiter.limit("60/minute")
async def search_case_law(request: Request, req: CaseLawSearchRequest):
    """Search the FL case-law corpus (Supabase legal_opinions).

    Hard rules enforced here:
      1. case_name / citation / court / date_filed / plain_english_summary
         come ONLY from corpus rows.
      2. courtlistener_url is reconstructed from the stored cluster_id (a
         real CourtListener ID) or null — never invented.
      3. No LLM is invoked.
    Supabase I/O is synchronous (supabase-py), so it is offloaded to a
    thread to avoid blocking the event loop.
    """
    query = _normalize(req.query)
    if not query:
        return apply_disclaimer(
            {"results": [], "total_results": 0, "query": req.query}, lang="en"
        )

    if _is_name_query(query):
        rows = await asyncio.to_thread(
            _search_case_name, query, req.court_filter, _RESULT_LIMIT
        )
        if len(rows) < _RESULT_LIMIT:
            extra = await asyncio.to_thread(
                _search_opinions_corpus, query, req.court_filter,
                _RESULT_LIMIT - len(rows),
            )
            known = {(r.get("cluster_id"), r.get("case_name")) for r in rows}
            for r in extra:
                key = (r.get("cluster_id"), r.get("case_name"))
                if key not in known:
                    rows.append(r)
                    known.add(key)
    else:
        rows = await asyncio.to_thread(
            _search_opinions_corpus, query, req.court_filter, _RESULT_LIMIT
        )

    if not rows and getattr(settings, "COURTLISTENER_TOKEN", ""):
        rows = await asyncio.to_thread(
            _courtlistener_v4_fallback, query, req.court_filter
        )

    cluster_ids = [
        r.get("cluster_id") for r in rows if r.get("cluster_id") is not None
    ]
    treatments = await asyncio.to_thread(_fetch_treatments, cluster_ids)
    for r in rows:
        cid = r.get("cluster_id")
        if cid is not None:
            r["_treatment"] = treatments.get(cid)

    results = [_row_to_result(r) for r in rows]
    return apply_disclaimer(
        {
            "results": results,
            "total_results": len(results),
            "query": req.query,
        },
        lang="en",
    )
