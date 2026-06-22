#!/usr/bin/env python3
"""Bridge: integrate legal-clear harvest repo into LegalClear main pipeline.

Reads harvest forms.jsonl → transforms → uploads PDFs to Supabase Storage
→ upserts court_forms rows → updates forms_manifest.json.

Usage (from repo root):
    cd backend
    uv run python ../scripts/bridge_harvest.py              # dry-run: plan only
    uv run python ../scripts/bridge_harvest.py --execute     # upload + upsert
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HARVEST_JSONL = Path("/home/hermes/workspace/legal-clear/forms-harvest/data/forms.jsonl")
HARVEST_BASE = Path("/home/hermes/workspace/legal-clear")
MANIFEST = REPO / "forms" / "forms_manifest.json"
BUCKET = "court-forms"

TQ_RANK = {"clean": 2, "ocr_noisy": 1, "empty": 0}


def load_env():
    env = REPO / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def norm_form_number(raw):
    if not raw:
        return None
    return re.sub(r"\s+", "", str(raw))


def slug(name):
    s = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
    s = re.sub(r"[^A-Za-z0-9/_().-]+", "_", s).strip("_")
    return s


def assign_key(entry):
    """Assign a catalog key matching ingest_forms.py logic."""
    fn = norm_form_number(entry.get("form_number"))
    if fn and re.match(r"^\d", fn):
        return fn  # statewide numbered form
    # County-local: key by county-form_number
    county = entry.get("county", "unknown")
    if county:
        pdf_path = entry.get("downloaded_path", "")
        if pdf_path:
            return slug(f"{county}/{Path(pdf_path).stem}")
    # Fallback
    if fn:
        return fn
    pdf_path = entry.get("downloaded_path", "")
    if pdf_path:
        return slug(Path(pdf_path).stem)
    return slug(entry.get("title", "unknown_form"))


def category_map(harvest_cat):
    """Map harvest categories to main pipeline categories."""
    mapping = {
        "county_local": "county_local",
        "family": "family_law",
        "small_claims": "small_claims",
        "civil": "civil",
        "criminal": "criminal",
        "probate": "probate",
        "traffic": "traffic",
    }
    return mapping.get(harvest_cat, "county_local")


def load_existing_manifest():
    if not MANIFEST.exists():
        return set()
    manifest = json.loads(MANIFEST.read_text())
    return {e.get("form_number", "") for e in manifest}


def load_harvest():
    """Load harvest entries, deduplicate within harvest by key."""
    entries = []
    with open(HARVEST_JSONL) as f:
        for line in f:
            entries.append(json.loads(line))

    # Assign keys and dedupe within harvest (keep first with PDF)
    by_key = {}
    for e in entries:
        key = assign_key(e)
        if key not in by_key:
            by_key[key] = e
        elif e.get("downloaded_path") and not by_key[key].get("downloaded_path"):
            by_key[key] = e  # prefer the one with a PDF

    return by_key


def build_plan():
    existing = load_existing_manifest()
    harvest = load_harvest()

    new_entries = {}
    skipped = []
    for key, entry in harvest.items():
        if key in existing:
            skipped.append(key)
            continue
        new_entries[key] = entry

    # Check PDF availability
    with_pdf = 0
    without_pdf = 0
    for key, entry in new_entries.items():
        path = entry.get("downloaded_path", "")
        if path:
            full = HARVEST_BASE / path if not path.startswith("/") else Path(path)
            if full.exists():
                with_pdf += 1
            else:
                without_pdf += 1
        else:
            without_pdf += 1

    return new_entries, skipped, with_pdf, without_pdf


def execute(new_entries, client):
    uploaded = inserted = failed = 0
    for key, entry in sorted(new_entries.items()):
        download_path = entry.get("downloaded_path", "")
        if not download_path:
            # No PDF — insert metadata only
            pdf_bytes = None
            sha = None
            object_path = None
        else:
            full = HARVEST_BASE / download_path if not download_path.startswith("/") else Path(download_path)
            if not full.exists():
                print(f"  ! missing PDF, metadata-only: {key}: {download_path}")
                pdf_bytes = None
                sha = None
                object_path = None
            else:
                pdf_bytes = full.read_bytes()
                sha = hashlib.sha256(pdf_bytes).hexdigest()
                object_path = f"harvest/{key}/{full.name}"
                try:
                    client.storage.from_(BUCKET).upload(
                        object_path, pdf_bytes,
                        file_options={"content-type": "application/pdf", "upsert": "true"},
                    )
                    uploaded += 1
                    print(f"  ✓ uploaded: {key} → {object_path}")
                except Exception as ex:
                    print(f"  ! upload failed {key}: {ex}")
                    failed += 1
                    continue

        # Build court_forms record
        source_url = entry.get("source_url", "")
        record = {
            "form_number": key,
            "title": (entry.get("title") or key)[:500],
            "category": category_map(entry.get("category", "county_local")),
            "source_page_url": source_url if source_url else None,
            "bucket_path": object_path,
            "content_hash": sha,
            "status": "review",
            "review_reason": "harvest_import",
            "last_changed_at": "now()",
            "updated_at": "now()",
        }
        try:
            client.table("court_forms").upsert(
                record, on_conflict="form_number"
            ).execute()
            inserted += 1
        except Exception as ex:
            print(f"  ! db upsert failed {key}: {ex}")
            failed += 1

    return uploaded, inserted, failed


def update_manifest(new_entries):
    """Append new entries to forms_manifest.json with harvest schema fields."""
    if not MANIFEST.exists():
        print("  ! manifest not found, skipping update")
        return

    manifest = json.loads(MANIFEST.read_text())

    for key, entry in sorted(new_entries.items()):
        download_path = entry.get("downloaded_path", "")
        manifest_entry = {
            "pdf_filename": download_path.replace(str(HARVEST_BASE) + "/", "") if download_path else None,
            "txt_filename": None,  # no text extraction yet
            "form_number": key,
            "title": entry.get("title"),
            "category": category_map(entry.get("category", "county_local")),
            "revision_date": entry.get("effective_date"),
            "source": entry.get("source_url") or "Harvest Import",
            "pdf_pages": None,
            "pdf_is_fillable": False,
            "pdf_bytes": None,
            "txt_char_count": 0,
            "text_quality": "empty",  # not yet extracted
            "notes": f"county={entry.get('county', '')} circuit={entry.get('circuit', '')} scope={entry.get('jurisdiction_scope', '')}",
        }
        manifest.append(manifest_entry)

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"  ✓ manifest updated: {len(manifest)} total entries")


def summarize(new_entries, skipped, with_pdf, without_pdf):
    print("\n── BRIDGE PLAN ─────────────────────────────────────────────")
    print(f"Harvest entries loaded:   {len(new_entries) + len(skipped)}")
    print(f"  Already in manifest:    {len(skipped)} (skip)")
    print(f"  New to import:          {len(new_entries)}")
    print(f"    With PDFs:            {with_pdf}")
    print(f"    Without PDFs:         {without_pdf}")

    # Category breakdown
    cats = defaultdict(int)
    for e in new_entries.values():
        cats[category_map(e.get("category", "county_local"))] += 1
    print("\n  Categories to import:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:25s} {count}")

    # County breakdown
    counties = defaultdict(int)
    for e in new_entries.values():
        c = e.get("county")
        if c:
            counties[c] += 1
    if counties:
        print(f"\n  Counties ({len(counties)}):")
        for c, count in sorted(counties.items(), key=lambda x: -x[1])[:15]:
            print(f"    {c:25s} {count}")
        if len(counties) > 15:
            print(f"    ... +{len(counties)-15} more")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="upload PDFs + upsert court_forms + update manifest")
    args = ap.parse_args()

    new_entries, skipped, with_pdf, without_pdf = build_plan()
    summarize(new_entries, skipped, with_pdf, without_pdf)

    if not args.execute:
        print("\n(dry-run — no network. Re-run with --execute to upload + write DB.)")
        return

    load_env()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in backend/.env")

    try:
        from supabase import create_client
    except ImportError:
        sys.exit("supabase package missing — run from backend/ via `uv run`.")

    client = create_client(url, key)

    print("\n── EXECUTING (upload + upsert) ──────────────────────────────")
    uploaded, inserted, failed = execute(new_entries, client)
    print(f"\nuploaded PDFs: {uploaded}  |  upserted rows: {inserted}  |  failed: {failed}")

    if inserted > 0:
        update_manifest(new_entries)

    print("\n── COMPLETE ─────────────────────────────────────────────────")
    print(f"Total new forms: {len(new_entries)}")
    print(f"Uploaded to Supabase: {uploaded}")
    print(f"Inserted into court_forms: {inserted}")


if __name__ == "__main__":
    main()
