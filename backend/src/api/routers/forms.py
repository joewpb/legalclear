"""Phase 2 — Form Catalog & Version-Aware Permanent Cache.

Serves official FL court forms from Supabase Storage through the LegalClear
domain. The court's servers are never contacted on the normal download path.
Change detection (POST /api/forms/check-updates) is the ONLY path that
contacts flcourts.gov, and only for targeted HEAD checks on known URLs.
"""

import hashlib
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse

from src.core.config import settings
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forms", tags=["forms"])
db = DatabaseManager()

FL_FAMILY_LAW_FORMS_PAGE = (
    "https://www.flcourts.gov/Resources-Services/"
    "Office-of-Family-Courts/Family-Law-Forms/"
)

BUCKET = "court-forms"


def _require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_forms(category: Optional[str] = None):
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
        raise HTTPException(status_code=500, detail="Could not list forms")


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
        raise HTTPException(status_code=502, detail="Could not retrieve form from storage")

    filename = storage_path.split("/")[-1]
    return StreamingResponse(
        iter([file_data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Change detection ──────────────────────────────────────────────────────────

@router.post("/check-updates", dependencies=[Depends(_require_api_key)])
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
              .eq("status", "active")
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
                head = await client.head(url)
                etag = head.headers.get("etag", "")
                content_length = head.headers.get("content-length", "")
                remote_sig = f"{etag}:{content_length}"

                if stored_hash and stored_hash == remote_sig:
                    # Unchanged — just update the checked timestamp
                    db.client.table("court_forms").update(
                        {"last_checked_at": "now()"}
                    ).eq("id", form_id).execute()
                    unchanged.append(form["form_number"])
                else:
                    # Changed (or first check) — re-pull the file
                    get_resp = await client.get(url)
                    get_resp.raise_for_status()
                    file_bytes = get_resp.content
                    sha256 = hashlib.sha256(file_bytes).hexdigest()

                    # Store new version alongside old (keep old for audit)
                    filename = url.split("/")[-1]
                    new_path = f"{form['form_number']}/{filename}"
                    db.client.storage.from_(BUCKET).upload(
                        new_path, file_bytes,
                        file_options={"content-type": "application/pdf",
                                      "upsert": "true"}
                    )

                    db.client.table("court_forms").update({
                        "content_hash": remote_sig,
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
