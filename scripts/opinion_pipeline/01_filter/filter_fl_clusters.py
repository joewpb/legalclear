#!/usr/bin/env python3
"""
Filter bulk CourtListener CSV files for FL opinions meeting Phase 1A criteria.
Joins opinion-clusters.csv + dockets.csv on docket_id → court_id.
Filters: court in (fla, fladistctapp), citation_count >= 20, date_filed >= 2010-01-01
Uses DictReader for column-name-based access, skips malformed rows.
"""

import csv
import bz2
import json
import os
import sys
from datetime import datetime, timezone, date

csv.field_size_limit(sys.maxsize)

RAW_DIR = "/home/hermes/legal_data/raw"
OUTPUT_FILE = "/home/hermes/legal_data/filtered_phase1a_clusters.json"

FL_COURTS = {"fla", "fladistctapp"}
MIN_CITE_COUNT = 20
MIN_DATE = date(2010, 1, 1)


def build_docket_map(dockets_path):
    """Build {docket_id: court_id} map for FL courts only."""
    print("Step 1: Indexing dockets for FL court mapping...")
    docket_court = {}
    docket_count = 0
    fl_count = 0
    skip_count = 0

    with bz2.open(dockets_path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            docket_count += 1
            court_id = row.get("court_id", "")
            if court_id in FL_COURTS:
                try:
                    docket_id = int(row["id"])
                    docket_court[docket_id] = court_id
                    fl_count += 1
                except (ValueError, KeyError):
                    skip_count += 1
            if docket_count % 500000 == 0:
                import sys as _sys
                print(f"  Scanned {docket_count:,} dockets... ({fl_count:,} FL so far)", file=_sys.stderr)

    print(f"  Total dockets scanned: {docket_count:,}")
    print(f"  FL dockets found: {fl_count:,}")
    print(f"  Skipped (parse errors): {skip_count:,}")
    return docket_court


def filter_clusters(clusters_path, docket_court):
    """Filter clusters by court, date, and citation count."""
    print("\nStep 2: Filtering clusters...")
    matched = []
    cluster_count = 0
    bad_rows = 0
    bad_court = 0
    bad_date = 0
    bad_cites = 0

    with bz2.open(clusters_path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cluster_count += 1
            try:
                # Check docket → court mapping
                docket_id_str = row.get("docket_id", "")
                if not docket_id_str:
                    bad_rows += 1
                    continue
                docket_id = int(docket_id_str)
                court_id = docket_court.get(docket_id)
                if court_id not in FL_COURTS:
                    bad_court += 1
                    continue

                # Check date
                date_str = row.get("date_filed", "")
                if not date_str:
                    bad_date += 1
                    continue
                filed = date.fromisoformat(date_str)
                if filed < MIN_DATE:
                    bad_date += 1
                    continue

                # Check citation count
                cite_str = row.get("citation_count", "0")
                cite_count = int(cite_str) if cite_str else 0
                if cite_count < MIN_CITE_COUNT:
                    bad_cites += 1
                    continue

                # Passed all filters
                matched.append({
                    "cluster_id": int(row["id"]),
                    "docket_id": docket_id,
                    "court_id": court_id,
                    "case_name": row.get("case_name", ""),
                    "date_filed": date_str,
                    "citation_count": cite_count,
                    "precedential_status": row.get("precedential_status", ""),
                    "source": row.get("source", "")
                })

                if len(matched) % 50 == 0:
                    import sys as _sys
                    print(f"  Found {len(matched)} matching clusters so far...", file=_sys.stderr)

            except Exception:
                bad_rows += 1

    print(f"\n  Total clusters scanned: {cluster_count:,}")
    print(f"  Bad/malformed rows: {bad_rows:,}")
    print(f"  Skipped (wrong court): {bad_court:,}")
    print(f"  Skipped (date < 2010): {bad_date:,}")
    print(f"  Skipped (cites < 20): {bad_cites:,}")
    print(f"  MATCHED: {len(matched)}")
    return matched


def main():
    clusters_path = os.path.join(RAW_DIR, "opinion-clusters-2026-03-31.csv.bz2")
    dockets_path = os.path.join(RAW_DIR, "dockets-2026-03-31.csv.bz2")

    for p in [clusters_path, dockets_path]:
        if not os.path.exists(p):
            print(f"Missing: {p}")
            sys.exit(1)

    docket_court = build_docket_map(dockets_path)

    matched = filter_clusters(clusters_path, docket_court)

    # Save results
    output = {
        "filter_params": {
            "courts": sorted(FL_COURTS),
            "min_citation_count": MIN_CITE_COUNT,
            "min_date": MIN_DATE.isoformat(),
            "bulk_source": "opinion-clusters-2026-03-31.csv.bz2 + dockets-2026-03-31.csv.bz2"
        },
        "total_matched": len(matched),
        "clusters": matched,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to: {OUTPUT_FILE}")

    # Also write plain cluster_id list for text fetcher
    id_list = [c["cluster_id"] for c in matched]
    id_path = os.path.join(RAW_DIR, "phase1a_cluster_ids.json")
    with open(id_path, "w") as f:
        json.dump(id_list, f)
    print(f"Cluster ID list: {id_path} ({len(id_list)} IDs)")


if __name__ == "__main__":
    main()
