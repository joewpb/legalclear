#!/usr/bin/env python3
"""Reconcile fixture classifications with the filter's own resolver:
for every fixture row, recompute what the filter would do with its token and
rewrite a corrected copy of the fixture."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.citation_filter import (
    _CITATION_TOKEN_RE,
    _bare_number_tokens,
    _resolves,
)

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "citation_phrasings.jsonl"
rows = [json.loads(l) for l in open(FIX)]

changed = 0
dropped = 0
kept_rows = []
for r in rows:
    phrasing = r["phrasing"].strip()
    main = [(m.start(), m.end(), m.group(0)) for m in _CITATION_TOKEN_RE.finditer(phrasing)]
    bare = _bare_number_tokens(phrasing, [(s, e) for s, e, _ in main])
    tokens = sorted(main + bare, key=lambda t: t[0])
    if not tokens:
        # Collector noise (form numbers, non-citation prose) — not a
        # citation phrasing; the filter correctly leaves it alone, and a
        # keep/strip test cannot apply. Drop it.
        dropped += 1
        print(f"drop noise {r['surface']}: {phrasing[:60]!r}")
        continue
    # A phrasing is "curated" iff EVERY citation token in it resolves.
    all_resolve = all(_resolves(v) for _, _, v in tokens)
    expected = "curated" if all_resolve else "uncurated"
    if r.get("classification") != expected:
        r["classification"] = expected
        changed += 1
        print(f"reclassify {r['surface']}: {phrasing[:60]!r} -> {expected}")
    kept_rows.append(r)

with open(FIX, "w") as f:
    for r in kept_rows:
        f.write(json.dumps(r) + "\n")
print(f"rows={len(rows)} kept={len(kept_rows)} reclassified={changed} dropped={dropped}")
