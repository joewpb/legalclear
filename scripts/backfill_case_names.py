#!/usr/bin/env python3
"""Backfill case_name for citation_treatment clusters from Orin clusters CSV."""
import bz2, csv, sys, subprocess, json
csv.field_size_limit(sys.maxsize)

CLUSTERS_CSV = "/home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2"

# Get treatment cluster IDs from Supabase (via stdin or hardcode)
print("Loading treatment cluster IDs from Orin citation_treatment.json...")
r = subprocess.run(
    ["cat", "/home/joe/legal_data/citation_treatment.json"],
    capture_output=True, text=True,
)
data = json.loads(r.stdout)
described = [d for d in data if d.get("direction") == "described"]
target_cids = set()
for d in described:
    cid = d.get("fl_cluster_id")
    if cid:
        target_cids.add(str(cid))
print(f"  {len(target_cids)} unique clusters to find")

# Scan clusters CSV
found = {}
print("Scanning clusters CSV...")
with bz2.open(CLUSTERS_CSV, "rt", encoding="utf-8", errors="replace") as f:
    for row in csv.DictReader(f):
        cid = (row.get("id") or "").strip()
        if cid in target_cids and cid not in found:
            name = (row.get("case_name") or "").strip()
            date = (row.get("date_filed") or "").strip()
            cite_count = row.get("citation_count") or "0"
            if name:
                found[cid] = {
                    "case_name": name[:200],
                    "date_filed": date[:10] if date else "",
                    "cite_count": int(cite_count) if cite_count.isdigit() else 0,
                }
                if len(found) % 500 == 0:
                    print(f"  found {len(found)}/{len(target_cids)}")

print(f"Found {len(found)}/{len(target_cids)} clusters with names")
# Output as JSON for backfill
with open("/home/joe/legal_data/treatment_case_names.json", "w") as f:
    json.dump(found, f, indent=2)
print("Saved to /home/joe/legal_data/treatment_case_names.json")
