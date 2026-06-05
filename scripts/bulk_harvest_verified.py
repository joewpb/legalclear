#!/usr/bin/env python3
"""
Bulk harvest for the 12 verified FL family law forms.

Downloads each PDF from its known flcourts.gov URL, uploads to Supabase
Storage, and marks the court_forms record active. Not a crawler — all 12
URLs are pre-confirmed from the seed CSV; no link discovery happens.

Usage (run from repo root):
    cd backend
    uv run python ../scripts/bulk_harvest_verified.py

    # Dry-run (download only, skip upload):
    uv run python ../scripts/bulk_harvest_verified.py --dry-run

Requirements: backend/.env must contain SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

import requests

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase package not found. Run: cd backend && uv sync")
    sys.exit(1)

BUCKET = "court-forms"
DELAY_SECONDS = 1.5  # polite pause between court server requests

# 12 forms confirmed in seed CSV (content_id verified against flcourts.gov).
# revision_date=None means "confirm at harvest" — left null in DB.
VERIFIED_FORMS = [
    {
        "form_number": "12.901(a)",
        "url": "https://www.flcourts.gov/content/download/685807/file_pdf/901a.pdf",
        "filename": "901a.pdf",
        "revision_date": "06/2025",
    },
    {
        "form_number": "12.901(b)(1)",
        "url": "https://www.flcourts.gov/content/download/685808/file_pdf/901b1.pdf",
        "filename": "901b1.pdf",
        "revision_date": "02/2018",
    },
    {
        "form_number": "12.901(b)(2)",
        "url": "https://www.flcourts.gov/content/download/685809/file_pdf/901b2.pdf",
        "filename": "901b2.pdf",
        "revision_date": "02/2018",
    },
    {
        "form_number": "12.901(b)(3)",
        "url": "https://www.flcourts.gov/content/download/685810/file_pdf/901b3.pdf",
        "filename": "901b3.pdf",
        "revision_date": "02/2018",
    },
    {
        "form_number": "12.902(c)",
        "url": "https://www.flcourts.gov/content/download/685813/file_pdf/12.902c.pdf",
        "filename": "12.902c.pdf",
        "revision_date": "06/2025",
    },
    {
        "form_number": "12.902(d)",
        "url": "https://www.flcourts.gov/content/download/685814/file_pdf/902d.pdf",
        "filename": "902d.pdf",
        "revision_date": None,  # confirm at harvest
    },
    {
        "form_number": "12.902(e)",
        "url": "https://www.flcourts.gov/content/download/685815/file_pdf/12.902e.pdf",
        "filename": "12.902e.pdf",
        "revision_date": "06/2025",
    },
    {
        "form_number": "12.902(f)(1)",
        "url": "https://www.flcourts.gov/content/download/685816/file_pdf/902f1.pdf",
        "filename": "902f1.pdf",
        "revision_date": "02/2018",
    },
    {
        "form_number": "12.903(b)",
        "url": "https://www.flcourts.gov/content/download/685823/file_pdf/903b.pdf",
        "filename": "903b.pdf",
        "revision_date": None,  # confirm at harvest
    },
    {
        "form_number": "12.903(c)(1)",
        "url": "https://www.flcourts.gov/content/download/685824/file_pdf/903c1.pdf",
        "filename": "903c1.pdf",
        "revision_date": "02/2018",
    },
    {
        "form_number": "12.905(a)",
        "url": "https://www.flcourts.gov/content/download/685834/file_pdf/905a.pdf",
        "filename": "905a.pdf",
        "revision_date": "11/2015",
    },
    {
        "form_number": "12.910(a)",
        "url": "https://www.flcourts.gov/content/download/685838/file_pdf/910a.pdf",
        "filename": "910a.pdf",
        "revision_date": None,  # confirm at harvest
    },
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "LegalClear/1.0 form-harvest (legalclear.io; non-commercial public-records access)",
})


def download_pdf(url: str) -> bytes:
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "pdf" not in content_type and len(resp.content) < 1000:
        raise ValueError(f"Response does not look like a PDF (content-type: {content_type})")
    return resp.content


def harvest_one(form: dict, client, dry_run: bool) -> bool:
    num = form["form_number"]
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Processing {num} ...")

    # Download
    try:
        pdf_bytes = download_pdf(form["url"])
    except Exception as e:
        print(f"  FAIL download: {e}")
        return False
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    print(f"  Downloaded {len(pdf_bytes):,} bytes  sha256={sha256[:16]}...")

    if dry_run:
        print(f"  (dry-run) would upload to {BUCKET}/{num}/{form['filename']}")
        return True

    # Check catalog record exists
    result = client.table("court_forms").select("id,status").eq("form_number", num).execute()
    if not result.data:
        print(f"  FAIL: '{num}' not found in court_forms table — run the Phase 2 migration first.")
        return False
    form_id = result.data[0]["id"]

    # Upload to bucket
    storage_path = f"{num}/{form['filename']}"
    try:
        client.storage.from_(BUCKET).upload(
            storage_path, pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
    except Exception as e:
        print(f"  FAIL upload: {e}")
        return False
    print(f"  Uploaded → {BUCKET}/{storage_path}")

    # Update catalog record
    update: dict = {
        "storage_path": storage_path,
        "content_hash": sha256,
        "status": "active",
        "last_checked_at": "now()",
        "last_changed_at": "now()",
    }
    if form["revision_date"]:
        update["court_revision_date"] = form["revision_date"]

    client.table("court_forms").update(update).eq("id", form_id).execute()
    print(f"  Marked active  revision_date={form['revision_date'] or '(not set)'}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Bulk-harvest the 12 verified FL family law forms")
    parser.add_argument("--dry-run", action="store_true", help="Download only; skip upload and DB update")
    args = parser.parse_args()

    if not args.dry_run:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
            sys.exit(1)
        client = create_client(url, key)
    else:
        client = None

    print(f"Harvesting {len(VERIFIED_FORMS)} verified forms{'  [DRY-RUN]' if args.dry_run else ''}")
    results = []
    for i, form in enumerate(VERIFIED_FORMS):
        ok = harvest_one(form, client, args.dry_run)
        results.append((form["form_number"], ok))
        if i < len(VERIFIED_FORMS) - 1:
            time.sleep(DELAY_SECONDS)

    passed = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    print(f"\n{'='*50}")
    print(f"Done: {len(passed)}/{len(VERIFIED_FORMS)} succeeded")
    if failed:
        print("Failed:")
        for num, _ in failed:
            print(f"  - {num}")
        sys.exit(1)
    else:
        print("All forms harvested and marked active." if not args.dry_run else "Dry-run complete.")


if __name__ == "__main__":
    main()
