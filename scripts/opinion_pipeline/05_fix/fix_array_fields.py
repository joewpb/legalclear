#!/usr/bin/env python3
"""Fix non-array fields in processed opinions for Supabase write."""
import json, os, re

PROC = "/home/hermes/legal_data/processed"
counts = {"parties": 0, "key_statutes": 0}

for fname in sorted(os.listdir(PROC)):
    if not fname.endswith(".json"): continue
    cid = int(fname.replace(".json",""))
    path = f"{PROC}/{fname}"
    d = json.load(open(path))
    p1 = d.get("pass1", {})
    changed = False

    # Fix parties
    parties = p1.get("parties", [])
    if isinstance(parties, dict):
        # Extract values as a flat list
        flat = []
        for k, v in parties.items():
            if isinstance(v, list):
                flat.extend(v)
            else:
                flat.append(str(v))
        p1["parties"] = flat
        counts["parties"] += 1
        changed = True
    elif isinstance(parties, str) and parties.strip():
        # Parse text like "Plaintiff v. Defendant" or "Appellant: X; Appellee: Y"
        text = parties.strip()
        parts = []
        for sep in [" v. ", " vs. ", " against "]:
            if sep in text:
                parts = text.split(sep, 1)
                break
        if not parts:
            for sep in [";"]:
                if sep in text:
                    parts = [s.split(":")[-1].strip() for s in text.split(sep)]
                    break
        if not parts:
            parts = [text]
        p1["parties"] = [p.strip() for p in parts if p.strip()]
        counts["parties"] += 1
        changed = True

    # Fix key_statutes
    statutes = p1.get("key_statutes", [])
    if isinstance(statutes, str):
        # Split on semicolons or newlines
        text = statutes.strip()
        if text:
            items = re.split(r'[;\n]+', text)
            p1["key_statutes"] = [s.strip() for s in items if s.strip()]
        else:
            p1["key_statutes"] = []
        counts["key_statutes"] += 1
        changed = True

    if changed:
        json.dump(d, open(path, "w"), indent=2)

print(f"Fixed parties: {counts['parties']}")
print(f"Fixed key_statutes: {counts['key_statutes']}")
