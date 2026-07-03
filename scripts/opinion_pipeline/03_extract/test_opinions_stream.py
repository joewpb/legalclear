#!/usr/bin/env python3
"""
Test opinion CSV parsing: stream from curl, stop after 1000 rows.
Uses PostgreSQL COPY escape format: \" for embedded quotes (not "").
"""

import csv
import bz2
import io
import json
import os
import sys
import subprocess

csv.field_size_limit(sys.maxsize)

RAW_DIR = "/home/hermes/legal_data/raw"
CLUSTER_IDS_PATH = os.path.join(RAW_DIR, "phase1a_cluster_ids.json")

with open(CLUSTER_IDS_PATH) as f:
    target_ids = set(json.load(f))
print(f"Target cluster IDs: {len(target_ids)}")

URL = "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data/opinions-2026-03-31.csv.bz2"

print("Starting stream: curl | bzcat | head -n 1001")
curl = subprocess.Popen(
    ["curl", "-s", URL],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
)
bz2_proc = subprocess.Popen(
    ["bzcat"],
    stdin=curl.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
)
head = subprocess.Popen(
    ["head", "-n", "1001"],
    stdin=bz2_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
)

# PostgreSQL CSV: " quoting, \ escape for embedded quotes, not ""
reader = csv.DictReader(
    io.TextIOWrapper(head.stdout, encoding="utf-8", errors="replace"),
    escapechar="\\",
    doublequote=False
)

row_count = 0
match_count = 0
errors = 0
sample_match = None
last_field_sizes = {}

for row in reader:
    row_count += 1
    try:
        cluster_id_str = row.get("cluster_id", "")
        if not cluster_id_str:
            continue
        cluster_id = int(cluster_id_str)

        for field in ["html_with_citations", "plain_text", "html"]:
            val = row.get(field, "")
            if len(val) > last_field_sizes.get(field, 0):
                last_field_sizes[field] = len(val)

        if cluster_id in target_ids:
            match_count += 1
            if sample_match is None:
                text = row.get("html_with_citations") or row.get("plain_text") or ""
                sample_match = {
                    "cluster_id": cluster_id,
                    "opinion_id": row.get("id", ""),
                    "html_with_citations_len": len(row.get("html_with_citations", "")),
                    "plain_text_len": len(row.get("plain_text", "")),
                    "text_preview": text[:300] if text else "(empty)"
                }
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  Parse error row {row_count}: {e}", file=sys.stderr)

# Clean up processes
for p in [head, bz2_proc, curl]:
    try:
        p.kill()
    except OSError:
        pass

print(f"\n=== TEST RESULTS ===")
print(f"Rows parsed: {row_count:,}")
print(f"Matches found: {match_count}")
print(f"Parse errors: {errors}")
print(f"Largest html_with_citations: {last_field_sizes.get('html_with_citations', 0):,} chars")
print(f"Largest plain_text: {last_field_sizes.get('plain_text', 0):,} chars")

if sample_match:
    print(f"\nSample match (cluster {sample_match['cluster_id']}):")
    print(f"  opinion_id: {sample_match['opinion_id']}")
    print(f"  html_with_citations: {sample_match['html_with_citations_len']:,} chars")
    print(f"  plain_text: {sample_match['plain_text_len']:,} chars")
    print(f"  Text preview:")
    print(f"    {sample_match['text_preview']}")
else:
    print("\nNo matches in first 1000 rows (expected — opinions not sorted by court)")

print(f"\n{'TEST PASSED' if errors == 0 else f'TEST PARTIAL: {errors} parse errors'}")
