#!/usr/bin/env python3
"""Shared-row text diff: prod court_rules vs Orin staged rules (non-FORM)."""
import json
import re
from pathlib import Path

prod = {}
for line in open(Path(__file__).resolve().parent.parent / "backups" / "court_rules_backup_20260820.jsonl"):
    r = json.loads(line)
    if r["rule_set"] in ("small_claims", "general_practice"):
        prod[r["rule_number"]] = r.get("text") or ""

orin = {}
for name in ("rules_small_claims", "rules_general_practice"):
    for line in open(f"/tmp/orin_stage/{name}.jsonl"):
        r = json.loads(line)
        if not (r.get("text") or "").lstrip().upper().startswith("FORM"):
            orin[r["rule_number"]] = r.get("text") or ""

shared = sorted(set(prod) & set(orin), key=lambda n: tuple(int(p) for p in n.split(".")))
print(f"shared rows: {len(shared)} | prod-only: {len(set(prod) - set(orin))} | orin-only non-form: {len(set(orin) - set(prod))}")


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


identical_bytes = sum(1 for n in shared if prod[n] == orin[n])
identical_norm = sum(1 for n in shared if prod[n] != orin[n] and norm(prod[n]) == norm(orin[n]))
differ = [n for n in shared if norm(prod[n]) != norm(orin[n])]
print(f"byte-identical: {identical_bytes}")
print(f"identical after whitespace normalization: {identical_norm}")
print(f"differing (normalized): {len(differ)}")
print("differing numbers:", " ".join(differ))

# save the pairs for the PDF-closeness comparison
out = Path("/tmp/shared_diffs.jsonl")
with open(out, "w") as f:
    for n in differ:
        f.write(json.dumps({"n": n, "prod": prod[n], "orin": orin[n]}) + "\n")
print(f"diffs written to {out}")
