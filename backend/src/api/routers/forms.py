"""Phase 2 — Form Catalog & Version-Aware Permanent Cache.

Serves official FL court forms from Supabase Storage through the LegalClear
domain. The court's servers are never contacted on the normal download path.
Change detection (POST /api/forms/check-updates) is the ONLY path that
contacts flcourts.gov, and only for targeted HEAD checks on known URLs.
"""

import hashlib
import json
import logging
import re
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.dependencies import require_api_key
from src.core.config import settings
from src.core.upl import apply_upl_guardrails, get_disclaimer
from src.memory.db import DatabaseManager
from src.services.form_recommender import (
    CASE_TYPES,
    DECISION_TREE,
    get_case_type,
    get_form_explanation,
    list_case_types,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forms", tags=["forms"])
db = DatabaseManager()

# Pinned model for every LLM call in this router.
SUGGEST_MODEL = "claude-sonnet-4-6"
_anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Statuses servable to end users (matches list_forms / download_form gating).
_SERVABLE = ["published", "active"]

FL_FAMILY_LAW_FORMS_PAGE = (
    "https://www.flcourts.gov/Resources-Services/"
    "Office-of-Family-Courts/Family-Law-Forms/"
)

BUCKET = "court-forms"


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_forms(category: str | None = None):
    """Return all active forms, optionally filtered by category."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        q = db.client.table("court_forms").select(
            "form_number,title,category,court_revision_date,"
            "situation_tags,plain_language_summary,source_page_url,status"
        ).in_("status", ["published", "active"])
        if category:
            q = q.eq("category", category)
        result = q.order("form_number").execute()
        return {"forms": result.data or []}
    except Exception as e:
        logger.error("list_forms failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not list forms") from e


# All Florida court forms in this database are valid statewide. The
# form_number prefix on harvested rows is scrape provenance (which clerk site
# the PDF came from), not jurisdiction, so it is not exposed as a filter.

def _sanitize_fts(q: str) -> str:
    """Strip characters that would break a PostgREST `or` / tsquery value."""
    return re.sub(r"[(),:&|!*<>]", " ", q).strip()


# Minimal stopword set for keyword extraction from a free-text situation.
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "have", "has", "had", "was",
    "were", "are", "from", "they", "them", "their", "what", "when", "where",
    "which", "would", "could", "should", "about", "into", "need", "needs",
    "want", "wants", "trying", "going", "been", "being", "will", "just",
    "some", "than", "then", "your", "you", "i'm", "i've", "florida", "court",
    "file", "filing", "form", "forms", "case", "legal", "help",
}


def _extract_keywords(situation: str, limit: int = 8) -> list[str]:
    """Pull salient keywords from a free-text situation description."""
    seen: list[str] = []
    for raw in re.findall(r"[A-Za-z]{4,}", situation.lower()):
        if raw in _STOPWORDS or raw in seen:
            continue
        seen.append(raw)
        if len(seen) >= limit:
            break
    return seen


def _candidate_forms_for_situation(situation: str, limit: int = 10) -> list[dict]:
    """Retrieve candidate forms for an AI suggestion via keyword scoring.

    A whole-sentence FTS query ANDs every term and matches almost nothing, so
    keywords are extracted and searched one at a time (FTS on form_text OR
    ilike on title). Forms are then ranked by how many DISTINCT keywords they
    match, so a form hitting several situation keywords outranks one that only
    matches a single common word.
    """
    keywords = _extract_keywords(situation)
    if not keywords:
        return []

    scores: dict[str, int] = {}
    rows: dict[str, dict] = {}
    for kw in keywords:
        res = (
            db.client.table("court_forms")
            .select(
                "form_number,title,category,plain_language_summary,situation_tags"
            )
            .in_("status", _SERVABLE)
            .or_(f"form_text.wfts(english).{kw},title.ilike.*{kw}*")
            .limit(40)
            .execute()
        )
        for row in res.data or []:
            fn = row["form_number"]
            scores[fn] = scores.get(fn, 0) + 1
            rows[fn] = row

    ranked = sorted(
        rows.values(),
        key=lambda r: (-scores[r["form_number"]], r["form_number"]),
    )
    return ranked[:limit]


def _search_court_forms(
    q: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Shared search over servable forms. Returns (rows, total).

    Full-text search uses the GIN tsvector index on form_text, OR-ed with an
    ilike match on title. Filters by category only.
    """
    query = (
        db.client.table("court_forms")
        .select(
            "form_number,title,category,plain_language_summary,"
            "situation_tags,source_page_url,status",
            count="exact",
        )
        .in_("status", _SERVABLE)
    )

    if q:
        cleaned = _sanitize_fts(q)
        if cleaned:
            query = query.or_(
                f"form_text.wfts(english).{cleaned},title.ilike.*{cleaned}*"
            )
    if category:
        query = query.eq("category", category)

    result = (
        query.order("form_number")
        .range(offset, offset + limit - 1)
        .execute()
    )

    rows = result.data or []
    total = result.count if result.count is not None else len(rows)
    return rows, total


# ── Recommend (deterministic decision tree) ────────────────────────────────

@router.get("/case-types")
async def get_case_types():
    """Return all 13 case types with their form requirements and fees."""
    cases = list_case_types()
    return {
        "case_types": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "court": c.court,
                "filing_fee": c.filing_fee,
                "form_numbers": c.form_numbers,
                "diy_florida": c.diy_florida,
                "diy_interview": c.diy_interview,
                "county_specific": c.county_specific,
                "note": c.note,
            }
            for c in cases
        ]
    }


@router.get("/recommend")
async def recommend_forms(case: str, county: str = ""):
    """Return recommended forms for a case type, backed by Supabase.

    Query params:
        case   — case type ID (e.g. divorce-with-children, small-claims)
        county — optional county name for circuit lookup and fee info

    Returns the case type metadata, plain-English form explanations,
    and the actual form records from the court_forms table when available.
    """
    case_type = get_case_type(case)
    if case_type is None:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(
            status_code=404,
            detail=f"Unknown case type: {case}. Use /api/forms/case-types for the full list.",
        )

    response: dict[str, Any] = {
        "case": {
            "id": case_type.id,
            "name": case_type.name,
            "description": case_type.description,
            "court": case_type.court,
            "filing_fee": case_type.filing_fee,
            "diy_florida": case_type.diy_florida,
            "diy_interview": case_type.diy_interview,
            "county_specific": case_type.county_specific,
            "note": case_type.note,
        },
        "forms": [],
    }

    # Look up each form in Supabase for full metadata
    if case_type.form_numbers and db.client is not None:
        try:
            result = (
                db.client.table("court_forms")
                .select(
                    "form_number,title,category,plain_language_summary,"
                    "situation_tags,source_page_url,status"
                )
                .in_("form_number", case_type.form_numbers)
                .in_("status", ["published", "active"])
                .order("form_number")
                .execute()
            )
            for row in result.data or []:
                fn = row.get("form_number", "")
                row["plain_explanation"] = get_form_explanation(fn)
                response["forms"].append(row)
        except Exception as e:
            logger.warning("recommend_forms: Supabase lookup failed — %s", e)

    # Fallback: add form entries not found in Supabase
    found_numbers = {f.get("form_number") for f in response["forms"]}
    for fn in case_type.form_numbers:
        if fn not in found_numbers:
            response["forms"].append({
                "form_number": fn,
                "title": None,
                "category": None,
                "plain_language_summary": None,
                "plain_explanation": get_form_explanation(fn),
                "source_page_url": None,
                "status": "not_in_catalog",
            })

    # County lookup
    if county and county.strip():
        from src.services.county_router import get_county_details
        try:
            county_info = get_county_details(county.strip())
            response["county"] = {
                "name": county_info["name"],
                "clerk_url": county_info.get("clerk_url", ""),
                "clerk_phone": county_info.get("clerk_phone", ""),
            }
        except Exception:
            logger.warning("County '%s' not found in lookup table, returning error", county, exc_info=True)
            response["county"] = {"name": county, "error": "County not found in lookup table"}

    return response


@router.get("/decision-tree")
async def get_decision_tree():
    """Return the full decision tree for interactive frontend use."""
    # Serialize — strip internal node IDs
    def serialize(node: dict) -> dict:
        out: dict[str, Any] = {"question": node["question"]}
        options = []
        for key, opt in node.get("options", {}).items():
            serialized: dict[str, Any] = {"id": key, "label": opt.get("label", key)}
            if "result" in opt:
                serialized["result"] = opt["result"]
            if "next" in opt:
                serialized["next"] = opt["next"]
            if "note" in opt:
                serialized["note"] = opt["note"]
            options.append(serialized)
        out["options"] = options
        return out

    return {
        "tree": {node_id: serialize(node) for node_id, node in DECISION_TREE.items()},
        "case_type_count": len(CASE_TYPES),
    }


# ── Search ──────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_forms(
    q: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Keyword + category search over servable forms, with pagination."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    try:
        rows, total = _search_court_forms(q, category, limit, offset)
    except Exception as e:
        logger.error("search_forms failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not search forms") from e

    return {
        "forms": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── Facets ──────────────────────────────────────────────────────────────────

@router.get("/facets")
async def form_facets():
    """Distinct categories (with counts) for the filter dropdown."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        result = (
            db.client.table("court_forms")
            .select("category")
            .in_("status", _SERVABLE)
            .execute()
        )
    except Exception as e:
        logger.error("form_facets failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not load facets") from e

    category_counts: dict[str, int] = {}
    for row in result.data or []:
        cat = row.get("category")
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "categories": [
            {"value": k, "count": v}
            for k, v in sorted(category_counts.items())
        ],
    }


# ── Metadata ─────────────────────────────────────────────────────────────────

@router.get("/meta/{form_number:path}")
async def form_meta(form_number: str):
    """Return JSON metadata for a single form (no PDF stream)."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        result = (
            db.client.table("court_forms")
            .select(
                "form_number,title,category,plain_language_summary,"
                "situation_tags,source_page_url,court_revision_date,status"
            )
            .eq("form_number", form_number)
            .execute()
        )
    except Exception as e:
        logger.error("form_meta failed for %s: %s", form_number, e)
        raise HTTPException(status_code=500, detail="Could not load form metadata") from e

    if not result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    return result.data[0]


# ── AI form suggestion (SSE) ─────────────────────────────────────────────────

SUGGEST_SYSTEM_PROMPT = (
    "You are a Florida court forms assistant for a legal information tool.\n"
    "A user has described their situation. Based on the forms provided,\n"
    "identify which forms are most relevant.\n"
    "RULES:\n"
    "Third person only. Never write \"you should\" or \"you must.\"\n"
    "Describe what each form is and what situation it addresses.\n"
    "Do not give legal advice. Do not state deadlines as obligations.\n"
    "Format: for each relevant form, output form_number, title, and\n"
    "a one-sentence plain description of when it is used.\n"
    "End with: \"This tool provides legal information only, not legal advice.\""
)


class SuggestRequest(BaseModel):
    situation: str = Field(..., min_length=1)


def _format_candidates(rows: list[dict]) -> str:
    """Render candidate forms as plain-text context for the model."""
    lines = []
    for r in rows:
        tags = ", ".join(r.get("situation_tags") or [])
        summary = r.get("plain_language_summary") or ""
        lines.append(
            f"- form_number: {r.get('form_number')}\n"
            f"  title: {r.get('title')}\n"
            f"  category: {r.get('category')}\n"
            f"  situation_tags: {tags}\n"
            f"  summary: {summary}"
        )
    return "\n".join(lines)


@router.post("/suggest")
async def suggest_forms(payload: SuggestRequest = Body(...)):
    """Stream AI-identified relevant forms for a described situation (SSE)."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # 1–2. Extract keywords from the situation and pull candidate forms.
    try:
        candidates = _candidate_forms_for_situation(payload.situation, limit=10)
    except Exception as e:
        logger.error("suggest_forms candidate search failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve forms") from e

    disclaimer = get_disclaimer("en")

    if not candidates:
        async def _empty():
            payload_obj = {
                "text": (
                    "No matching Florida court forms were found for that "
                    "description. Adjusting the wording or browsing by "
                    "category may surface relevant forms."
                )
            }
            yield f"data: {json.dumps(payload_obj)}\n\n"
            yield f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_empty(), media_type="text/event-stream")

    user_message = (
        f"Situation described: {payload.situation}\n\n"
        f"Candidate Florida court forms:\n{_format_candidates(candidates)}"
    )

    async def _stream():
        collected: list[str] = []
        try:
            async with _anthropic.messages.stream(
                model=SUGGEST_MODEL,
                max_tokens=1500,
                system=[
                    {
                        "type": "text",
                        "text": SUGGEST_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                async for chunk in stream.text_stream:
                    collected.append(chunk)
                    yield f"data: {json.dumps({'text': chunk})}\n\n"

            # Apply UPL guardrails to the full AI response and always append
            # the standard disclaimer.
            guarded = apply_upl_guardrails("".join(collected), "en")
            if guarded.strip() != "".join(collected).strip():
                logger.warning("suggest_forms: UPL guardrails flagged output")
            yield f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("suggest_forms stream failed: %s", e)
            error_payload = {
                "error": True,
                "message": "Suggestions could not be generated.",
                "disclaimer": disclaimer,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/{form_number:path}")
async def download_form(form_number: str):
    """Stream a form from the Supabase Storage bucket.

    Never contacts the court on this path.
    Returns 451 (Unavailable For Legal Reasons) for stale/withdrawn forms
    with a pointer to the court's page so the user can get the current copy.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    result = (db.client.table("court_forms")
              .select("form_number,title,status,storage_path,source_page_url")
              .eq("form_number", form_number)
              .execute())

    if not result.data:
        raise HTTPException(status_code=404, detail="Form not found")

    form = result.data[0]
    status = form.get("status")

    if status in ("stale", "withdrawn"):
        court_page = form.get("source_page_url") or FL_FAMILY_LAW_FORMS_PAGE
        raise HTTPException(
            status_code=451,
            detail={
                "error": "form_not_current",
                "message": (
                    "This form has been updated or withdrawn by the court. "
                    "Please download the current version directly from the "
                    "Florida Courts website."
                ),
                "court_page": court_page,
            }
        )

    if status not in ("published", "active"):
        raise HTTPException(
            status_code=404,
            detail="Form is not yet available for download."
        )

    storage_path = form.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=404, detail="Form file not found in storage")

    try:
        file_data = db.client.storage.from_(BUCKET).download(storage_path)
    except Exception as e:
        logger.error("Storage download failed for %s: %s", form_number, e)
        raise HTTPException(status_code=502, detail="Could not retrieve form from storage") from e

    filename = storage_path.split("/")[-1]
    return StreamingResponse(
        iter([file_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Change detection ──────────────────────────────────────────────────────────

@router.post("/check-updates", dependencies=[Depends(require_api_key)])
async def check_updates():
    """Lightweight change-detection pass over all active forms.

    For each form with a source_download_url:
    - HEAD the URL; compare ETag / Content-Length against stored content_hash.
    - If unchanged: update last_checked_at only.
    - If changed: re-pull the file, store the new copy, update metadata,
      set status='stale' to gate serving until a human reviews the new version.

    This is the ONLY endpoint that contacts flcourts.gov.
    It makes one targeted HEAD (and one GET if changed) per form —
    never a crawl.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    result = (db.client.table("court_forms")
              .select("id,form_number,source_download_url,content_hash,storage_path")
              .in_("status", ["published", "active"])
              .not_.is_("source_download_url", "null")
              .execute())

    forms = result.data or []
    updated = []
    unchanged = []
    errors = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for form in forms:
            form_id = form["id"]
            url = form["source_download_url"]
            stored_hash = form.get("content_hash")

            try:
                # Download and compute SHA-256 for content comparison
                get_resp = await client.get(url)
                get_resp.raise_for_status()
                file_bytes = get_resp.content
                sha256 = hashlib.sha256(file_bytes).hexdigest()

                if stored_hash and stored_hash == sha256:
                    # Unchanged — just update the checked timestamp
                    db.client.table("court_forms").update(
                        {"last_checked_at": "now()"}
                    ).eq("id", form_id).execute()
                    unchanged.append(form["form_number"])
                else:
                    # Changed (or first check) — store new version
                    filename = url.split("/")[-1]
                    new_path = f"{form['form_number']}/{filename}"
                    db.client.storage.from_(BUCKET).upload(
                        new_path, file_bytes,
                        file_options={"content-type": "application/pdf",
                                      "upsert": "true"}
                    )

                    db.client.table("court_forms").update({
                        "content_hash": sha256,
                        "storage_path": new_path,
                        "last_checked_at": "now()",
                        "last_changed_at": "now()",
                        # Gate serving until a human reviews the new version
                        "status": "stale" if stored_hash else "active",
                    }).eq("id", form_id).execute()

                    updated.append(form["form_number"])

            except Exception as e:
                logger.error("check-updates failed for %s: %s", form["form_number"], e)
                errors.append({"form_number": form["form_number"], "error": str(e)})

    return {
        "checked": len(forms),
        "unchanged": unchanged,
        "updated_flagged_stale": updated,
        "errors": errors,
    }
