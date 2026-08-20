#!/usr/bin/env python3
"""Compare prod vs Orin text against the official PDF for every differing
shared rule. Uses the harvest parser's rule extraction on the cached official
PDFs, then difflib similarity against both versions."""
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_rules import extract_rules  # noqa: E402

PDFS = {
    "2": Path("/tmp/lc_rules_harvest/general_practice.pdf"),
    "7": Path("/tmp/lc_rules_harvest/small_claims.pdf"),
}


def norm(t):
    return re.sub(r"\s+", " ", t).strip()


official: dict[str, str] = {}
for prefix, pdf in PDFS.items():
    if not pdf.exists():
        print(f"PDF missing: {pdf}")
        continue
    for num, title, body in extract_rules(pdf):
        official[num] = norm(body)


def sim(a, b):
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


diffs = [json.loads(l) for l in open("/tmp/shared_diffs.jsonl")]
results = []
missing_pdf = []
for d in diffs:
    n = d["n"]
    off = official.get(n)
    if off is None:
        missing_pdf.append(n)
        continue
    sp, so = sim(norm(d["prod"]), off), sim(norm(d["orin"]), off)
    verdict = "prod" if sp > so else ("orin" if so > sp else "tie")
    results.append((n, sp, so, verdict, sp - so))

prod_wins = [r for r in results if r[3] == "prod"]
orin_wins = [r for r in results if r[3] == "orin"]
ties = [r for r in results if r[3] == "tie"]
print(f"compared against official PDF: {len(results)} | missing from my PDF parse: {len(missing_pdf)}")
print(f"  prod closer: {len(prod_wins)} | orin closer: {len(orin_wins)} | tie: {len(ties)}")
print(f"  mean |prod-off| - |orin-off|: {sum(abs(r[4]) for r in results)/max(len(results),1):.4f}")
print("prod-closer rules:", " ".join(r[0] for r in prod_wins))
print("orin-closer rules:", " ".join(r[0] for r in orin_wins))
print("ties:", " ".join(r[0] for r in ties))
if missing_pdf:
    print("missing from official parse:", " ".join(missing_pdf))
# detail lines for the extremes
print("\nlargest gaps (rule, prod_sim, orin_sim, winner):")
for r in sorted(results, key=lambda x: -abs(x[4]))[:12]:
    print(f"  {r[0]}: prod={r[1]:.3f} orin={r[2]:.3f} -> {r[3]}")
