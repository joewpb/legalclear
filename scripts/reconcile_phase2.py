#!/usr/bin/env python3
"""Phase 2 reconciliation: link bucket files to court_forms records.

For every 12.xxx folder in the court-forms bucket:
  1. Find the matching court_forms record
  2. Identify the PDF file in the folder
  3. Set storage_path + content_hash
  4. Promote to 'published' if it has a valid PDF

Run from repo root:
    cd backend
    uv run python ../scripts/reconcile_phase2.py              # dry-run
    uv run python ../scripts/reconcile_phase2.py --execute    # write DB
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_env():
    env = REPO / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="write to DB")
    args = ap.parse_args()

    load_env()
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, key)

    # List all folders in the bucket
    all_items = client.storage.from_("court-forms").list("", {"limit": 500})
    folders_12 = sorted(
        [f["name"] for f in all_items if f["name"].startswith("12.")]
    )
    print(f"12.xxx folders in bucket: {len(folders_12)}")

    # Get all 12.xxx court_forms records
    db_records = (
        client.table("court_forms")
        .select("id,form_number,title,status,storage_path,content_hash")
        .ilike("form_number", "12.%")
        .execute()
    )
    db_index = {r["form_number"]: r for r in db_records.data}
    print(f"12.xxx records in DB:     {len(db_index)}")

    to_update = []   # (id, storage_path, content_hash, new_status)
    missing_db = []  # bucket folder with no DB record
    no_pdf = []      # bucket folder with no PDF
    already_ok = 0

    for folder in folders_12:
        if folder not in db_index:
            missing_db.append(folder)
            continue

        record = db_index[folder]

        # Skip if already has storage_path set (check if it still exists)
        if record.get("storage_path"):
            # Verify the file still exists
            try:
                client.storage.from_("court-forms").download(record["storage_path"])
                already_ok += 1
                continue
            except Exception:
                pass  # File missing, re-link

        # List files in the bucket folder
        try:
            files = client.storage.from_("court-forms").list(folder)
        except Exception as e:
            no_pdf.append((folder, str(e)))
            continue

        # Find the PDF file (prefer simpler/shorter names)
        pdfs = [f for f in files if f["name"].lower().endswith(".pdf")]
        if not pdfs:
            no_pdf.append((folder, "no PDF in folder"))
            continue

        # Prefer the shortest PDF name (usually the canonical one)
        pdfs.sort(key=lambda f: len(f["name"]))
        pdf_file = pdfs[0]
        storage_path = f"{folder}/{pdf_file['name']}"

        # Download and hash
        try:
            file_bytes = client.storage.from_("court-forms").download(storage_path)
            content_hash = hashlib.sha256(file_bytes).hexdigest()
        except Exception as e:
            no_pdf.append((folder, f"download failed: {e}"))
            continue

        new_status = "published" if record["status"] not in ("published", "active") else record["status"]
        to_update.append((record["id"], storage_path, content_hash, new_status))

    # Summary
    print(f"Already OK (storage_path set + verified): {already_ok}")
    print(f"To update:                                 {len(to_update)}")
    print(f"Missing DB record:                         {len(missing_db)}")
    print(f"No PDF in folder:                          {len(no_pdf)}")

    if missing_db:
        print("\nBucket folders with NO DB record:")
        for fn in missing_db:
            print(f"  {fn}")

    if no_pdf:
        print("\nFolders with PDF issues:")
        for fn, reason in no_pdf:
            print(f"  {fn}: {reason}")

    if to_update and args.execute:
        print(f"\nWriting {len(to_update)} updates to DB...")
        for row_id, sp, ch, ns in to_update:
            client.table("court_forms").update({
                "storage_path": sp,
                "content_hash": ch,
                "status": ns,
            }).eq("id", row_id).execute()
        print("Done.")
    elif to_update:
        print("\n(dry-run — re-run with --execute to write)")
        for row_id, sp, ch, ns in to_update[:5]:
            record = next(r for r in db_index.values() if r["id"] == row_id)
            print(f"  {record['form_number']}: {sp} ({record['status']} -> {ns})")
        if len(to_update) > 5:
            print(f"  ... +{len(to_update)-5} more")

    print(f"\nAfter reconciliation: {already_ok + len(to_update)}/{len(folders_12)} folders servable")


if __name__ == "__main__":
    main()
