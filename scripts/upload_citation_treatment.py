#!/usr/bin/env python3
"""
Upload citation treatment data from Orin JSON to Supabase.
Reads /home/joe/legal_data/citation_treatment.json (from Orin),
deduplicates by cluster_id + treatment_type, and upserts to
Supabase citation_treatment table.

Run on the VPS which has the Supabase service key.
"""
import json, os, sys

# Load Supabase creds
env_path = os.path.expanduser("/home/hermes/workspace/legalclear/backend/.env")
url = key = ""
for line in open(env_path):
    line = line.strip()
    if line.startswith("SUPABASE_URL="):
        url = line.split("=", 1)[1]
    if line.startswith("SUPABASE_SERVICE_KEY="):
        key = line.split("=", 1)[1]

if not url or not key:
    print("FATAL: Could not load Supabase credentials")
    sys.exit(1)

import httpx

REST_URL = f"{url}/rest/v1"
TABLE = "citation_treatment"
HEADERS = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

# Load treatment data from Orin
import subprocess

print("Fetching treatment data from Orin...")
r = subprocess.run(
    ["ssh", "joe@100.117.93.67", "cat", "/home/joe/legal_data/citation_treatment.json"],
    capture_output=True, text=True,
)
if r.returncode != 0:
    print(f"SSH failed: {r.stderr}")
    sys.exit(1)

data = json.loads(r.stdout)
print(f"  {len(data)} raw records loaded")

# Only keep 'described' direction — FL cases that WERE treated negatively
described = [d for d in data if d.get("direction") == "described"]
print(f"  {len(described)} FL cases treated negatively (direction=described)")

# Classify treatment type
def classify(text):
    t = text.lower()
    if "overrul" in t:
        return "overruled"
    if "revers" in t:
        return "reversed"
    if "supersed" in t:
        return "superseded"
    if "abrogat" in t:
        return "abrogated"
    if "critici" in t or "distinguish" in t:
        return "criticized"
    if "question" in t or "disapprov" in t or "declined to follow" in t:
        return "questioned"
    return "other"

# Deduplicate: keep one record per cluster_id + treatment_type, highest score
seen: dict[tuple[int, str], dict] = {}
for d in described:
    cid = d.get("fl_cluster_id")
    if cid is None:
        continue
    ttype = classify(d["treatment_text"])
    key = (cid, ttype)
    if key not in seen or d.get("score", 0) > seen[key].get("score", 0):
        seen[key] = d

records = list(seen.values())
print(f"  {len(records)} unique cluster+treatment combinations")

# Upload in batches
BATCH = 50
uploaded = 0
for i in range(0, len(records), BATCH):
    batch = records[i : i + BATCH]
    rows = []
    for d in batch:
        rows.append({
            "cluster_id": d["fl_cluster_id"],
            "treatment_type": classify(d["treatment_text"]),
            "treatment_text": d["treatment_text"][:500],
            "direction": "described",
            "score": d.get("score", 0),
        })

    resp = httpx.post(
        f"{REST_URL}/{TABLE}",
        headers=HEADERS,
        json=rows,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        uploaded += len(rows)
        print(f"  batch {i // BATCH + 1}: {len(rows)} rows OK ({uploaded}/{len(records)})")
    else:
        print(f"  batch {i // BATCH + 1}: FAILED {resp.status_code} — {resp.text[:200]}")

print(f"\nDone. {uploaded} records uploaded to Supabase {TABLE}.")
