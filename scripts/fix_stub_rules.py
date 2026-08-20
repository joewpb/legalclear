#!/usr/bin/env python3
"""Job 2: re-extract confirmed stub rows from official sources + update prod.
Backup first; per-row before/after char counts; leave + name anything that
can't be re-extracted cleanly."""
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

TARGETS = {
    "probate": ["5.901", "5.905", "5.910"],
    "civil_procedure": ["1.190"],
    "criminal": ["3.214", "3.250", "3.260", "3.270", "3.505", "3.990", "3.991", "3.992"],
}
PDFS = {
    "probate": Path("/tmp/lc_rules_harvest/probate.pdf"),
    "civil_procedure": Path("/tmp/lc_rules_harvest/civil_procedure.pdf"),
}

official_pdf: dict[str, str] = {}
for set_name, pdf in PDFS.items():
    for num, title, body in extract_rules(pdf):
        official_pdf[num] = re.sub(r"\s+", " ", body).strip()

# criminal: last-occurrence span from the raw cache text
CACHE = Path.home() / ".hermes/cache/web/www-media.floridabar.org-36c69b54db.md"
raw = CACHE.read_text()
hdr = re.compile(r"RULE\s+(3\.\d+(?:\.\d+)*)\s*\.?", re.IGNORECASE)
positions = [(m.start(), m.end(), m.group(1)) for m in hdr.finditer(raw)]
official_crim: dict[str, str] = {}
for i, (start, end, num) in enumerate(positions):
    if num not in TARGETS["criminal"]:
        continue
    # body = from this header's end to the next header with a DIFFERENT number
    j = i + 1
    while j < len(positions) and positions[j][2] == num:
        j += 1
    block = raw[end:positions[j][0]] if j < len(positions) else raw[end:]
    block = re.sub(r"Florida Rules of Criminal Procedure\s*\w+\s+\d+,?\s*\d*\s*\d+", " ", block)
    block = re.sub(r"\s+", " ", block).strip()
    official_crim[num] = block

rows = json.loads(open("/tmp/rules_audit.json").read())
target_rows = [r for r in rows if r["rule_set"] in TARGETS and r["rule_number"] in TARGETS[r["rule_set"]]]
print(f"target rows: {len(target_rows)}")

# backup
with open("/home/hermes/workspace/legalclear/backups/court_rules_pre_stubfix_20260820.jsonl", "w") as f:
    for r in target_rows:
        f.write(json.dumps(r) + "\n")
print("backup written: court_rules_pre_stubfix_20260820.jsonl")

from supabase import create_client  # noqa: E402

supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])

for r in target_rows:
    n = r["rule_number"]
    new_text = official_pdf.get(n) or official_crim.get(n)
    before = len(r["text"] or "")
    if not new_text:
        print(f"  {r['rule_set']} {n}: NO CLEAN RE-EXTRACTION — left as-is ({before} chars)")
        continue
    after = len(new_text)
    if after < before:
        print(f"  {r['rule_set']} {n}: official shorter ({before}->{after}) — KEPT existing")
        continue
    supabase.table("court_rules").update({"text": new_text}).eq("rule_set", r["rule_set"]).eq("rule_number", n).execute()
    print(f"  {r['rule_set']} {n}: {before} -> {after} chars UPDATED")
