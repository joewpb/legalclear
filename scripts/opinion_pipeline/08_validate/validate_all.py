#!/usr/bin/env python3
"""Step 2: Full validation of all 759 processed records."""
import json, os, sys

PROC = "/home/hermes/legal_data/processed"
files = sorted(os.listdir(PROC))

LABELS = ["WHAT HAPPENED", "THE RULE", "WHAT THE COURT DECIDED", "WHY THIS MAY MATTER"]

total = 0
passing = 0
flagged = []

for fname in files:
    if not fname.endswith(".json"): continue
    cid = int(fname.replace(".json",""))
    d = json.load(open(f"{PROC}/{fname}"))
    total += 1

    notes = []

    # 1. cluster_id present, int
    cid_val = d.get("cluster_id")
    if cid_val is None or not isinstance(cid_val, int):
        notes.append(f"cluster_id missing or non-int: {type(cid_val).__name__}")

    # 2. case_name present, non-empty
    cn = d.get("case_name", "")
    if not cn or not isinstance(cn, str) or not cn.strip():
        notes.append("case_name missing or empty")

    # 3. summary_plain is STRING, >= 200 chars, all 4 labels
    sp = d.get("pass2", {}).get("summary_plain", "")
    if not isinstance(sp, str):
        notes.append(f"summary_plain not string: {type(sp).__name__}")
    else:
        if len(sp) < 200:
            notes.append(f"summary_plain too short: {len(sp)} chars")
        missing = [l for l in LABELS if l not in sp]
        if missing:
            notes.append(f"summary_plain missing labels: {missing}")

    # 4. situation_tags non-empty array
    tags = d.get("pass1", {}).get("situation_tags", [])
    if not isinstance(tags, list) or len(tags) == 0:
        notes.append(f"situation_tags empty or not array: {type(tags).__name__} len={len(tags) if isinstance(tags,list) else 'N/A'}")

    # 5. attorney_prompt present, non-empty
    ap = d.get("pass2", {}).get("attorney_prompt", "")
    if not ap or not isinstance(ap, str) or not ap.strip():
        notes.append("attorney_prompt missing or empty")

    if notes:
        # Flag the record
        d["quality_flagged"] = True
        d["quality_notes"] = "; ".join(notes)
        json.dump(d, open(f"{PROC}/{fname}", "w"), indent=2)
        flagged.append({"cluster_id": cid, "reasons": notes})
    else:
        passing += 1
        # Ensure clean if previously flagged but now passing
        if d.get("quality_flagged"):
            d.pop("quality_flagged", None)
            d.pop("quality_notes", None)
            json.dump(d, open(f"{PROC}/{fname}", "w"), indent=2)

print(f"Total: {total}")
print(f"Passing: {passing}")
print(f"Flagged: {len(flagged)}")
if flagged:
    print(f"\nFlagged records:")
    for f in flagged:
        print(f"  {f['cluster_id']}: {'; '.join(f['reasons'])}")
