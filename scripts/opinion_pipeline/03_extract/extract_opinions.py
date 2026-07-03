#!/usr/bin/env python3
"""
Full streaming extraction: curl opinion CSV → bzcat → filter for 759 FL
opinions → save as normalized JSON to staging.
Runs in streaming mode — never stores the full 54 GB file on disk.
Deletes the compressed file after processing.
"""

import csv
import io
import json
import os
import sys
import subprocess
from datetime import datetime, timezone

csv.field_size_limit(sys.maxsize)

RAW_DIR = "/home/hermes/legal_data/raw"
STAGING_DIR = "/home/hermes/legal_data/staging"
CLUSTER_IDS_PATH = os.path.join(RAW_DIR, "phase1a_cluster_ids.json")
EXTRACTION_LOG = "/home/hermes/legal_data/extraction_log.json"

# Load target cluster IDs
with open(CLUSTER_IDS_PATH) as f:
    target_ids = set(json.load(f))
print(f"Target cluster IDs to extract: {len(target_ids)}")

# Track results
results = {
    "extracted": 0,
    "empty_text": 0,
    "errors": 0,
    "not_found": 0,
    "matched_ids": set(),
    "empty_text_ids": [],
    "error_ids": [],
    "missing_ids": set(target_ids),
    "text_field_used": {"html_with_citations": 0, "plain_text": 0, "none": 0}
}

URL = "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data/opinions-2026-03-31.csv.bz2"

print("Starting full streaming extraction: curl | bzcat")
curl = subprocess.Popen(
    ["curl", "-s", URL],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
)
bz2_proc = subprocess.Popen(
    ["bzcat"],
    stdin=curl.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
)

reader = csv.DictReader(
    io.TextIOWrapper(bz2_proc.stdout, encoding="utf-8", errors="replace"),
    escapechar="\\",
    doublequote=False
)

row_count = 0
last_report = datetime.now()

for row in reader:
    row_count += 1

    try:
        cluster_id_str = row.get("cluster_id", "")
        if not cluster_id_str:
            continue
        cluster_id = int(cluster_id_str)
    except ValueError:
        continue

    if cluster_id not in target_ids:
        continue

    # We have a match!
    results["missing_ids"].discard(cluster_id)
    results["matched_ids"].add(cluster_id)

    try:
        # Get text: prefer html_with_citations, fall back to plain_text
        text = row.get("html_with_citations", "") or ""
        text_source = "html_with_citations"
        if not text:
            text = row.get("plain_text", "") or ""
            text_source = "plain_text"
        if not text:
            text = row.get("html", "") or ""
            text_source = "html"

        results["text_field_used"][text_source] = results["text_field_used"].get(text_source, 0) + 1

        if not text:
            results["empty_text"] += 1
            results["empty_text_ids"].append(cluster_id)
            continue

        # Build record
        record = {
            "cluster_id": cluster_id,
            "opinion_id": int(row.get("id", 0)),
            "case_name": "",  # Not in opinions CSV — fetched from cluster data
            "court_id": "",   # Not in opinions CSV
            "date_filed": "",  # Not in opinions CSV
            "cite_count": 0,   # Not in opinions CSV
            "status": "",
            "precedential_status": "",
            "opinion_text": text,
            "text_source": text_source,
            "opinion_type": row.get("type", ""),
            "download_url": row.get("download_url", ""),
            "local_path": row.get("local_path", ""),
            "page_count": row.get("page_count"),
            "extracted_by_ocr": row.get("extracted_by_ocr", ""),
            "sha1": row.get("sha1", ""),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "ingest_source": "courtlistener_phase1a_bulk"
        }

        staging_path = os.path.join(STAGING_DIR, f"{cluster_id}.json")
        with open(staging_path, "w") as f:
            json.dump(record, f, indent=2)

        results["extracted"] += 1

    except Exception as e:
        results["errors"] += 1
        results["error_ids"].append(cluster_id)
        print(f"  Error extracting cluster {cluster_id}: {e}", file=sys.stderr)

    # Progress report
    now = datetime.now()
    if (now - last_report).total_seconds() > 30:
        elapsed = (now - last_report).total_seconds()
        print(f"  Rows: {row_count:,} | Extracted: {results['extracted']} | "
              f"Empty: {results['empty_text']} | Errors: {results['errors']} | "
              f"Remaining: {len(results['missing_ids'])}")
        last_report = now

# Clean up
for p in [bz2_proc, curl]:
    try:
        p.kill()
    except OSError:
        pass

# Calculate not_found
results["not_found"] = len(results["missing_ids"])
results["missing_ids_list"] = sorted(results["missing_ids"])

print(f"\n{'='*60}")
print(f"EXTRACTION COMPLETE")
print(f"  Total rows scanned: {row_count:,}")
print(f"  Extracted: {results['extracted']}")
print(f"  Empty text (skipped): {results['empty_text']}")
print(f"  Errors: {results['errors']}")
print(f"  Not found in CSV: {results['not_found']}")
print(f"  Text source: {results['text_field_used']}")
if results["empty_text_ids"]:
    print(f"  Empty text cluster IDs: {results['empty_text_ids'][:20]}{'...' if len(results['empty_text_ids']) > 20 else ''}")
if results["missing_ids_list"]:
    print(f"  Not-found cluster IDs: {results['missing_ids_list'][:20]}{'...' if len(results['missing_ids_list']) > 20 else ''}")
print(f"  Staging: {STAGING_DIR}/")

# Clean up — remove the compressed file
compressed_path = os.path.join(RAW_DIR, "opinions-2026-03-31.csv.bz2")
if os.path.exists(compressed_path):
    os.remove(compressed_path)
    print(f"  Deleted: {compressed_path}")

# Save extraction log
results["missing_ids_list"] = sorted(results["missing_ids"])
results["completed_at"] = datetime.now(timezone.utc).isoformat()
with open(EXTRACTION_LOG, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"  Log: {EXTRACTION_LOG}")
