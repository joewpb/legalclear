#!/usr/bin/env python3
"""
Phase 2 harvest helper — upload a single court form PDF to Supabase Storage
and mark its court_forms record as active.

Usage (run from repo root):
    cd backend
    uv run python ../scripts/harvest_form.py \
        --form-number "12.901(a)" \
        --pdf-path "/path/to/downloaded/901a.pdf" \
        --revision-date "06/2025"

Requirements: backend/.env must contain SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Load .env from backend/
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


def main():
    parser = argparse.ArgumentParser(description="Upload a court form to Supabase Storage")
    parser.add_argument("--form-number", required=True, help='e.g. "12.901(a)"')
    parser.add_argument("--pdf-path", required=True, help="Local path to the downloaded PDF")
    parser.add_argument("--revision-date", default=None, help='e.g. "06/2025"')
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        sys.exit(1)

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    client = create_client(url, key)

    # Check that the form exists in the catalog
    result = client.table("court_forms").select("id,form_number,status").eq(
        "form_number", args.form_number
    ).execute()

    if not result.data:
        print(f"ERROR: form_number '{args.form_number}' not found in court_forms table.")
        print("Seed the catalog first (Phase 2 migration).")
        sys.exit(1)

    form = result.data[0]
    print(f"Found: {form['form_number']} (current status: {form['status']})")

    # Read and hash the file
    file_bytes = pdf_path.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    storage_path = f"{args.form_number}/{pdf_path.name}"

    print(f"Uploading to bucket '{BUCKET}' at path '{storage_path}' ...")
    try:
        client.storage.from_(BUCKET).upload(
            storage_path, file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
    except Exception as e:
        print(f"ERROR: Upload failed: {e}")
        sys.exit(1)

    # Update the catalog record
    update = {
        "storage_path": storage_path,
        "content_hash": sha256,
        "status": "active",
        "last_checked_at": "now()",
        "last_changed_at": "now()",
    }
    if args.revision_date:
        update["court_revision_date"] = args.revision_date

    client.table("court_forms").update(update).eq("id", form["id"]).execute()
    print(f"✓  {args.form_number} is now active in the catalog.")
    print(f"   storage_path : {storage_path}")
    print(f"   sha256       : {sha256}")


if __name__ == "__main__":
    main()
