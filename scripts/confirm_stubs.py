#!/usr/bin/env python3
"""Confirm suspected stubs: prod text vs official PDF text per rule.

Official sources: gp/sc/civpro/probate/appellate PDFs via extract_rules;
criminal via the cache-derived official blocks. A row is a CONFIRMED stub if
the official block is substantially longer (>=3x) or similarity < 0.5 while
the official block is >= 500 chars. Genuinely short = official block also
short (ratio ~1)."""
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_rules import extract_rules  # noqa: E402
from harvest_criminal_from_cache import candidates  # noqa: E402

PDF_PREFIX = {
    "general_practice.pdf": "2",
    "small_claims.pdf": "7",
    "civil_procedure.pdf": "1",
    "probate.pdf": "5",
    "appellate.pdf": "9",
}
PDFS = {name: Path(f"/tmp/lc_rules_harvest/{name}") for name in PDF_PREFIX}

official: dict[str, str] = {}
for name, prefix in PDF_PREFIX.items():
    if PDFS[name].exists():
        for num, title, body in extract_rules(PDFS[name]):
            official.setdefault(num, body)

# criminal official blocks (longest fragment join, same logic as the harvest)
for num, frags in candidates.items():
    if len(frags) > 1:
        official.setdefault(num, " ".join(frags[1:]))
    elif frags:
        official.setdefault(num, frags[0])


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


rows = json.loads(open("/tmp/rules_audit.json").read())
KNOWN_SHORT = {"3.702", "3.703", "3.704", "3.480"}
suspects = [r for r in rows if len(r["text"] or "") < 500 and r["rule_number"] not in KNOWN_SHORT]

confirmed, genuine, missing = [], [], []
for r in suspects:
    off = official.get(r["rule_number"])
    if off is None:
        missing.append(r)
        continue
    own_n, off_n = norm(r["text"]), norm(off)
    s = sim(own_n, off_n)
    if len(off_n) >= 500 and (len(off_n) >= 3 * len(own_n) or s < 0.5):
        confirmed.append((r, len(r["text"] or ""), len(off_n), s))
    else:
        genuine.append((r, len(r["text"] or ""), len(off_n), s))

print(f"suspects compared: {len(suspects)} | confirmed stubs: {len(confirmed)} | genuinely short: {len(genuine)} | official missing: {len(missing)}")
print("\n== CONFIRMED STUBS ==")
for r, own, off, s in sorted(confirmed, key=lambda x: x[1]):
    print(f"  {r['rule_set']} {r['rule_number']}: own={own} official={off} sim={s:.2f}")
print("\n== GENUINELY SHORT (verified against official) ==")
for r, own, off, s in sorted(genuine, key=lambda x: x[2]):
    print(f"  {r['rule_set']} {r['rule_number']}: own={own} official={off} sim={s:.2f}")
print("\n== OFFICIAL BLOCK MISSING (unverifiable, named) ==")
for r in missing:
    print(f"  {r['rule_set']} {r['rule_number']}: {len(r['text'] or '')} chars")

json.dump({
    "confirmed": [{"rule_set": r["rule_set"], "rule_number": r["rule_number"]} for r, *_ in confirmed],
    "genuine": [{"rule_set": r["rule_set"], "rule_number": r["rule_number"]} for r, *_ in genuine],
    "missing": [{"rule_set": r["rule_set"], "rule_number": r["rule_number"]} for r in missing],
}, open("/tmp/stub_verdicts.json", "w"), indent=2)
print("\nverdicts saved to /tmp/stub_verdicts.json")
