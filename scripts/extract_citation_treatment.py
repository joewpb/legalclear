#!/usr/bin/env python3
"""
Extract citation treatment (history) data from CourtListener CLUSTERS CSV.
Matches FL cases via the pre-built fl_cluster_court.csv map (8.4MB, fast).
Only extracts rows with non-empty history field.

Runs ON the Orin where the 2.3GB CSV lives.
"""
import bz2, csv, json, sys
csv.field_size_limit(sys.maxsize)

CLUSTERS_CSV = "/home/joe/legal_data/opinion-clusters-2026-03-31.csv.bz2"
FL_MAP = "/home/joe/legal_data/fl_cluster_court.csv"
OUTPUT = "/home/joe/legal_data/citation_treatment.json"

def safe_int(val, default=0):
    s = (val or "").strip()
    return int(s) if s.isdigit() else default

def main():
    # Load FL cluster ID set (fast — 8.4MB, 426K rows)
    print("Loading FL cluster map...")
    fl_ids = set()
    with open(FL_MAP) as f:
        for row in csv.DictReader(f):
            cid = (row.get("cluster_id") or "").strip()
            if cid:
                fl_ids.add(cid)
    print("  {} FL clusters loaded".format(len(fl_ids)))

    # Scan clusters CSV
    results = []
    scanned = 0
    matched = 0
    with_history = 0

    print("Scanning clusters CSV...")
    with bz2.open(CLUSTERS_CSV, "rt", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            scanned += 1
            cid = (row.get("id") or "").strip()
            if cid not in fl_ids:
                if scanned % 500000 == 0:
                    print("  scanned {:,}, matched={}, w/history={}".format(
                        scanned, matched, with_history))
                continue

            matched += 1
            history = (row.get("history") or "").strip()
            if not history:
                continue

            with_history += 1
            results.append({
                "cluster_id": int(cid),
                "case_name": (row.get("case_name") or "")[:200],
                "citation_count": safe_int(row.get("citation_count")),
                "history": history,
                "disposition": (row.get("disposition") or "")[:500],
                "date_filed": row.get("date_filed") or "",
                "precedential_status": row.get("precedential_status") or "",
            })

            if with_history % 10 == 0:
                print("  {} with history (scanned {:,}, matched {})".format(
                    with_history, scanned, matched))

    print("\nDone. Scanned {:,} rows, {} FL matched, {} with history".format(
        scanned, matched, with_history))

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print("Saved {} records to {}".format(len(results), OUTPUT))

    for r in results[:3]:
        print("\n  Cluster {}: {}".format(r["cluster_id"], r["case_name"][:70]))
        print("  history: {}".format(r["history"][:250]))

if __name__ == "__main__":
    main()
