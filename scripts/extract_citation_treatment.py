#!/usr/bin/env python3
"""
Extract citation TREATMENT data for FL cases from CourtListener parentheticals CSV.

Parentheticals describe HOW a later case treated an earlier one:
  "overruled by", "criticized by", "distinguished by", etc.

Matches by cross-referencing described_opinion_id against our known FL cluster IDs.
Filters for negative treatment keywords in the parenthetical text.

Input:
  /home/joe/legal_data/parentheticals-2026-03-31.csv.bz2 (285 MB)
  /home/joe/legal_data/fl_cluster_court.csv               (FL cluster map)

Output:
  /home/joe/legal_data/citation_treatment.json
"""
import bz2, csv, json, re, sys
csv.field_size_limit(sys.maxsize)

PARENTHETICALS_CSV = "/home/joe/legal_data/parentheticals-2026-03-31.csv.bz2"
FL_MAP = "/home/joe/legal_data/fl_cluster_court.csv"
OUTPUT = "/home/joe/legal_data/citation_treatment.json"

# Negative treatment signals to detect in parenthetical text.
# Case-insensitive regex patterns.
NEGATIVE_TREATMENT = re.compile(
    r"\b(overruled|overruling|reversed|reversing|abrogated|abrogating|"
    r"superseded|superseding|called into question|questioned|"
    r"disapproved|declined to follow|disagreed with|"
    r"not followed|no longer good law|limited by|"
    r"criticized|criticising|distinguished)\b",
    re.IGNORECASE,
)


def safe_int(val, default=0):
    """Parse int from possibly-corrupted field."""
    s = (val or "").strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    """Parse float from possibly-corrupted field."""
    if val is None:
        return default
    try:
        return float(str(val).strip().strip('"').strip("'"))
    except (ValueError, TypeError):
        return default


def main():
    # Load FL cluster IDs
    print("Loading FL cluster map...")
    fl_ids = set()
    with open(FL_MAP) as f:
        for row in csv.DictReader(f):
            cid = (row.get("cluster_id") or "").strip()
            if cid:
                fl_ids.add(cid)
    print("  {} FL clusters loaded".format(len(fl_ids)))

    # Also map opinion_id -> cluster_id for cross-referencing
    # Parentheticals use opinion_id, not cluster_id.
    # We need to convert. Build from Orin PostgreSQL.
    print("Loading opinion_id → cluster_id map from PostgreSQL...")
    import subprocess
    r = subprocess.run(
        ["psql", "-U", "joe", "-d", "legal_clear", "-t", "-A",
         "-c", "SELECT opinion_id, cluster_id FROM opinions WHERE court_id IN ('fla','fladistctapp')"],
        capture_output=True, text=True,
    )
    op_to_cluster = {}
    for line in r.stdout.strip().split("\n"):
        parts = line.split("|")
        if len(parts) == 2:
            op_to_cluster[parts[0].strip()] = parts[1].strip()
    print("  {} FL opinion IDs mapped".format(len(op_to_cluster)))
    fl_op_ids = set(op_to_cluster.keys())

    # Scan parentheticals
    results = []
    scanned = 0
    hits = 0
    negative = 0

    print("Scanning parentheticals CSV...")
    with bz2.open(PARENTHETICALS_CSV, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scanned += 1
            described = (row.get("described_opinion_id") or "").strip()
            describing = (row.get("describing_opinion_id") or "").strip()

            # Check if either opinion is Florida
            fl_opinion = None
            other_opinion = None
            if described in fl_op_ids:
                fl_opinion = described
                other_opinion = describing
            elif describing in fl_op_ids:
                fl_opinion = describing
                other_opinion = described

            if fl_opinion is None:
                if scanned % 5000000 == 0:
                    print("  scanned {:,}, hits={}, negative={}".format(
                        scanned, hits, negative))
                continue

            hits += 1
            text = row.get("text") or ""

            # Check for negative treatment
            if not NEGATIVE_TREATMENT.search(text):
                continue

            negative += 1
            fl_cluster = op_to_cluster.get(fl_opinion)

            results.append({
                "fl_opinion_id": safe_int(fl_opinion),
                "fl_cluster_id": safe_int(fl_cluster) if fl_cluster and fl_cluster.isdigit() else None,
                "other_opinion_id": safe_int(other_opinion) if other_opinion.isdigit() else None,
                "treatment_text": text[:500],
                "direction": "described" if described == fl_opinion else "describing",
                "score": safe_float(row.get("score")),
            })

            if negative % 10 == 0:
                print("  {} negative treatments found (scanned {:,}, hits={})".format(
                    negative, scanned, hits))

    print("\nDone.")
    print("  Scanned: {:,} rows".format(scanned))
    print("  FL hits: {}".format(hits))
    print("  Negative treatment: {}".format(negative))

    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print("  Saved {} records to {}".format(len(results), OUTPUT))

    # Show samples
    for r in results[:5]:
        print("\n  FL opinion {} (cluster {}): {}".format(
            r["fl_opinion_id"], r["fl_cluster_id"], r["treatment_text"][:200]))


if __name__ == "__main__":
    main()
