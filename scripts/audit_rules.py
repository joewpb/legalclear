#!/usr/bin/env python3
"""Stub-audit of the full court_rules corpus (Decision 12 standard)."""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_rules import extract_rules  # noqa: E402

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from supabase import create_client  # noqa: E402

supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])
rows = []
offset = 0
while True:
    resp = supabase.table("court_rules").select(
        "citation,rule_set,rule_number,title,text,source_url"
    ).range(offset, offset + 9999).execute()
    batch = resp.data or []
    if not batch:
        break
    rows.extend(batch)
    offset += len(batch)

print(f"court_rules rows: {len(rows)}")
by_set: dict[str, list[dict]] = {}
for r in rows:
    by_set.setdefault(r["rule_set"] or "?", []).append(r)

print("\n== length distribution by rule set ==")
all_lens = []
for s in sorted(by_set):
    lens = sorted(len((r["text"] or "")) for r in by_set[s])
    all_lens.extend(lens)
    n = len(lens)
    under500 = [r for r in by_set[s] if len(r["text"] or "") < 500]
    print(f"{s}: rows={n} min={lens[0]} median={lens[n//2]} max={lens[-1]} under500={len(under500)}")

all_lens.sort()
print(f"\nALL: min={all_lens[0]} median={all_lens[len(all_lens)//2]} max={all_lens[-1]}")

# suspected stubs: under 500 chars, excluding the four already-verified shorties
KNOWN_SHORT = {"3.702", "3.703", "3.704", "3.480"}
print("\n== suspected stubs (under 500 chars, all listed) ==")
suspects = []
for r in rows:
    n = len(r["text"] or "")
    if n < 500:
        tag = "known-short(verified)" if r["rule_number"] in KNOWN_SHORT else "SUSPECTED"
        suspects.append((r, n, tag))
        print(f"  {r['rule_set']} {r['rule_number']}: {n} chars [{tag}]")

# body detection: heading-only = text stripped of first title line + history/notes leaves < 100 chars of non-trivia
HISTORY_RE = re.compile(r"(?:History\.|Committee Notes|Court Commentary|Adopted|Amended).*$", re.IGNORECASE | re.DOTALL)


def body_len(r):
    t = r["text"] or ""
    # drop title line if present
    if r.get("title") and t.lstrip().upper().startswith((r["title"].strip().upper()[:20] or "XX")):
        t = t[len(r["title"]):]
    t = HISTORY_RE.sub("", t)
    return len(re.sub(r"\s+", " ", t).strip())


print("\n== body detection (heading-only check) ==")
heading_only = [r for r in rows if body_len(r) < 100 and r["rule_number"] not in KNOWN_SHORT]
print(f"heading-only rows: {len(heading_only)}")
for r in heading_only:
    print(f"  {r['rule_set']} {r['rule_number']}: body_after_strip={body_len(r)} title={str(r.get('title'))[:50]}")

out = Path("/tmp/rules_audit.json")
out.write_text(json.dumps(rows))
print(f"\naudit rows saved to {out}")
