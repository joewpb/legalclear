"""FL Case Law Lookup router — Phase 22.

Source: phases/source/PHASE_22_case_law.md

RAG-only architecture: CourtListener's public search API supplies every
case name, citation, court, date, and URL. The LLM is permitted ONLY to
write a 2-sentence plain-English summary of the snippet CourtListener
returns. Any result missing an `absolute_url` is dropped before
returning — no fabricated URLs are ever sent to the client.

This is the sanctions-protection layer for LegalClear. See Mata v.
Avianca (2023) for the precedent that made hallucinated citations a
disciplinary event.

Path note: source put this at backend/src/api/routes/case_law.py; repo
location is backend/src/api/routers/ (Phase 10 divergence). HTTP
endpoints unchanged.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from anthropic import Anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.config import settings
from src.core.upl import apply_disclaimer

router = APIRouter(prefix="/api/case-law")
logger = logging.getLogger(__name__)

# Court filters → CourtListener court IDs.
#   fl_supreme    — Florida Supreme Court
#   fl_appellate  — Florida District Courts of Appeal
#   federal_fl    — FL federal districts + 11th Circuit
COURT_MAP: dict[str, Optional[str]] = {
    "fl_supreme": "fla",
    "fl_appellate": "flaapp",
    "federal_fl": "flmd,flnd,flsd,ca11",
    "all": None,
}

_CL_SEARCH_URL = "https://www.courtlistener.com/api/rest/v3/search/"
_CL_BASE = "https://www.courtlistener.com"

_SUMMARY_SYSTEM_PROMPT = (
    "You write 2-sentence plain-English summaries of legal opinion "
    "snippets. Do NOT invent case names, citations, or court "
    "information. If the snippet is too short or ambiguous to "
    "summarize, return an empty string."
)


class CaseLawSearchRequest(BaseModel):
    query: str
    court_filter: str = "all"


def _summarize_snippet(client: Anthropic, snippet: str) -> Optional[str]:
    """Return a 2-sentence plain-English summary or None on any failure.

    The LLM is explicitly forbidden from generating cite-bearing fields;
    this function is the ONLY place it gets to write anything.
    """
    if not snippet:
        return None
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=[
                {
                    "type": "text",
                    "text": _SUMMARY_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarize this opinion snippet in 2 plain-English "
                        f"sentences for a non-lawyer: {snippet}"
                    ),
                }
            ],
        )
        text = msg.content[0].text.strip() if msg.content else ""
        return text or None
    except Exception as e:  # noqa: BLE001 — graceful degradation per spec
        logger.warning(
            "case-law summary call failed (%s); returning result without summary",
            type(e).__name__,
        )
        return None


@router.post("/search")
async def search_case_law(req: CaseLawSearchRequest):
    """Search FL case law via CourtListener.

    Hard rules enforced here:
      1. case_name / citation / court / date_filed / courtlistener_url
         come ONLY from CourtListener's response.
      2. Any result missing an `absolute_url` is dropped — never invented.
      3. The LLM is invoked only to write the optional `plain_english_summary`.
    """
    params: dict[str, str] = {"q": req.query, "type": "o"}
    mapped = COURT_MAP.get(req.court_filter)
    if mapped:
        params["court"] = mapped

    async with httpx.AsyncClient() as http:
        try:
            cl = await http.get(_CL_SEARCH_URL, params=params, timeout=15.0)
            cl.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"CourtListener unavailable: {e}",
            )

    cl_data = cl.json()
    raw_results = cl_data.get("results", [])[:10]

    client = Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        max_retries=1,
        timeout=30.0,
    )

    enriched: list[dict] = []
    for r in raw_results:
        absolute_url = r.get("absolute_url")
        if not absolute_url:
            # HARD RULE: never fabricate a URL. Drop the result instead.
            continue

        # CourtListener may return either a relative path ("/opinion/...")
        # or, very rarely, a full URL. Normalize so the client receives a
        # value that always starts with the canonical base.
        cl_full_url = (
            absolute_url
            if absolute_url.startswith(_CL_BASE)
            else f"{_CL_BASE}{absolute_url}"
        )

        citation_field = r.get("citation")
        if isinstance(citation_field, list):
            citation_str = citation_field[0] if citation_field else ""
        elif isinstance(citation_field, str):
            citation_str = citation_field
        else:
            citation_str = ""

        enriched.append(
            {
                "case_name": r.get("caseName", "Unknown case name"),
                "citation": citation_str,
                "court": r.get("court", "Unknown court"),
                "date_filed": r.get("dateFiled", ""),
                "plain_english_summary": _summarize_snippet(
                    client, r.get("snippet", "")
                ),
                "courtlistener_url": cl_full_url,
            }
        )

    return apply_disclaimer({
        "results": enriched,
        "total_results": cl_data.get("count", 0),
        "query": req.query,
    }, lang="en")
