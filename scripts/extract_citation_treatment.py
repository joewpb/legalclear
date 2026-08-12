#!/usr/bin/env python3
"""
Extract citation treatment (history) data from CourtListener bulk CSV.
Scans opinion-clusters CSV for FL cases with non-empty history field.
Outputs JSON for Supabase import.

Data sources on Orin:
  /home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2  (2.3GB)
  /home/joe/legal_data/fl_cluster_court.csv                  (8.4MB, cluster_id→court_id map)

Output:
  /home/joe/legal_data/citation_treatment.json
"""
import csv
import json
import sys

# Increase CSV field limit — some columns (syllabus, headnotes) are huge.
csv.field_size_limit(sys.maxsize)

CLUSTERS_CSV = "/home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2"
FL_MAP = "/home/joe/legal_data/fl_cluster_court.csv"
OUTPUT = "/home/joe/legal_data/citation_treatment.json"

def main():
    # Load FL cluster IDs from the pre-filtered map (fast — 8MB)
    print("Loading FL cluster map...")
    fl_clusters: set[str] = set()
    with open(FL_MAP) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("cluster_id") or "").strip()
            if cid:
                fl_clusters.add(cid)
    print(f"  {len(fl_clusters)} FL clusters loaded")

    # Scan clusters CSV for treatment data
    print("Scanning clusters CSV for history data...")
    import bz2
    results: list[dict] = []
    scanned = 0
    matched = 0

    with bz2.open(CLUSTERS_CSV, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scanned += 1
            cid = (row.get("id") or "").strip()
            if cid not in fl_clusters:
                if scanned % 500000 == 0:
                    print(f"  scanned {scanned:,} rows, {matched} matched...")
                continue

            history = (row.get("history") or "").strip()
            if not history:
                continue

            matched += 1
            results.append({
                "cluster_id": int(cid),
                "case_name": (row.get("case_name") or "")[:200],
                "citation_count": int(row.get("citation_count") or 0),
                "history": history,
                "disposition": (row.get("disposition") or "")[:500],
                "date_filed": row.get("date_filed") or "",
                "court_id": row.get("court_id") or "",
                "precedential_status": row.get("precedential_status") or "",
            })

            if matched % 50 == 0:
                print(f"  matched {matched} so far (scanned {scanned:,})...")

    print(f"\nDone. Scanned {scanned:,} rows, {matched} FL clusters with history data.")

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} records to {OUTPUT}")

    # Show a few samples
    for r in results[:3]:
        print(f"\n  Cluster {r['cluster_id']}: {r['case_name'][:70]}")
        print(f"  history: {r['history'][:250]}")

if __name__ == "__main__":
    main()
