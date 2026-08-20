#!/usr/bin/env python3
"""Per-rule best-side merge of court_rules text: official PDF as arbiter.
For the 82 shared rules, pick the side (prod or Orin) closer to the official
PDF text; UPDATE prod rows where Orin wins. Prod-closer and whitespace-
identical rows are left untouched."""
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_rules import extract_rules  # noqa: E402

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

PDFS = {
    "2": Path("/tmp/lc_rules_harvest/general_practice.pdf"),
    "7": Path("/tmp/lc_rules_harvest/small_claims.pdf"),
}
RULE_SET = {"2": "general_practice", "7": "small_claims"}


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


official: dict[str, str] = {}
for prefix, pdf in PDFS.items():
    for num, title, body in extract_rules(pdf):
        official[num] = norm(body)

prod_rows = {}
for line in open(Path(__file__).resolve().parent.parent / "backups" / "court_rules_backup_20260820.jsonl"):
    r = json.loads(line)
    if r["rule_set"] in ("small_claims", "general_practice"):
        prod_rows[r["rule_number"]] = r

orin_texts = {}
for name in ("rules_small_claims", "rules_general_practice"):
    for line in open(f"/tmp/orin_stage/{name}.jsonl"):
        r = json.loads(line)
        if not (r.get("text") or "").lstrip().upper().startswith("FORM"):
            orin_texts[r["rule_number"]] = r.get("text") or ""

wins_orin = []
wins_prod = []
for n in sorted(prod_rows, key=lambda x: tuple(int(p) for p in x.split("."))):
    off = official.get(n)
    if off is None:
        continue
    p, o = norm(prod_rows[n]["text"]), norm(orin_texts.get(n, ""))
    sp, so = sim(p, off), sim(o, off)
    if so > sp + 1e-6:
        wins_orin.append((n, sp, so))
    else:
        wins_prod.append(n)

print(f"official arbiter: {len(official)} rules")
print(f"Orin wins (to update): {len(wins_orin)}")
print(f"prod wins / tie (untouched): {len(wins_prod)}")

# backup the rows we're about to change
changed = [prod_rows[n] for n, _, _ in wins_orin]
with open("/home/hermes/workspace/legalclear/backups/court_rules_premerge_36.jsonl", "w") as f:
    for r in changed:
        f.write(json.dumps(r) + "\n")
print(f"pre-merge backup: {len(changed)} rows -> backups/court_rules_premerge_36.jsonl")

from supabase import create_client  # noqa: E402

supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])
updated = 0
failed = []
for n, sp, so in wins_orin:
    text = orin_texts[n]
    rs = RULE_SET[n.split(".")[0]]
    try:
        resp = supabase.table("court_rules").update({"text": text}).eq("rule_set", rs).eq("rule_number", n).execute()
        updated += 1
    except Exception as e:  # noqa: BLE001
        failed.append(f"{n}: {type(e).__name__}: {e}")

print(f"updated: {updated} | failed: {len(failed)}")
for f in failed:
    print(f"  {f}")
