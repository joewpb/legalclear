#!/usr/bin/env python3
"""Extract criminal rules (3.x) from the web_extract-cached full text of the
official Criminal Procedure PDF (single-line markdown), validate, and upsert
into court_rules. Longest-block-per-number defeats the TOC."""
import os
import re
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

CACHE = Path.home() / ".hermes/cache/web/www-media.floridabar.org-36c69b54db.md"
SRC = "https://www-media.floridabar.org/uploads/2026/07/2026_01-JUL-Criminal-Procedure-Rules-7-13-2026-1.pdf"
MIN_BODY = 120
DRY = "--dry-run" in sys.argv

text = CACHE.read_text()
# page-header noise line (appears inline in the single-line markdown)
PAGE_NOISE = re.compile(r"Florida Rules of Criminal Procedure\s+July 13,\s*2026\s+\d+\s*")

hdr = re.compile(r"RULE\s+(3\.\d+(?:\.\d+)*)\s*\.?", re.IGNORECASE)

# Position-based blocking: each block runs from one header to the next.
# The TOC blocks are short (title + page number); the body blocks are long.
# Longest block per number wins.
matches = list(hdr.finditer(text))
candidates: dict[str, list[str]] = {}
for idx, m in enumerate(matches):
    num = m.group(1)
    end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
    block = text[m.end():end]
    block = PAGE_NOISE.sub(" ", block)
    block = re.sub(r"\s+", " ", block).strip()
    # trim trailing section-title noise ("VII. SUBSTITUTION OF JUDGE") that
    # precedes the next rule's header
    block = re.sub(r"\s+(?:[IVX]+\.\s+[A-Z][A-Z ,.'-]{3,120})$", "", block)
    candidates.setdefault(num, []).append(block)

rows = []
fails = []
for num in sorted(candidates, key=lambda n: tuple(int(x) for x in n.split("."))):
    frags = candidates[num]
    # The PDF repeats the rule number as a running page header, splitting
    # multi-page rules into fragments. Fragment 0 is the TOC entry; the rest
    # are body pages — join them (continuation headers may repeat the title,
    # acceptable corpus-level noise).
    if len(frags) > 1:
        body = " ".join(frags[1:])
    else:
        body = frags[0]
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) < MIN_BODY:
        fails.append(f"3.x {num}: body {len(body)} chars < {MIN_BODY}")
        continue
    rows.append({
        "citation": f"Fla. R. Crim. P. {num}",
        "rule_set": "criminal",
        "rule_number": num,
        "subsection": None,
        "title": body[:200],
        "text": body,
        "source_url": SRC,
        "jurisdiction": "FL",
    })

print(f"3.x rules: {len(rows)} loadable, {len(fails)} failures")
for f in fails:
    print(f"  FAIL: {f}")
for num in ("3.220", "3.140", "3.020"):
    hits = [r for r in rows if r["rule_number"] == num]
    if hits:
        b = hits[0]["text"]
        print(f"SPOT {num}: {len(b)} chars | head: {b[:100]!r}")
    else:
        print(f"SPOT {num}: MISSING")

if DRY:
    sys.exit(0)

from supabase import create_client  # noqa: E402
supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])
for i in range(0, len(rows), 100):
    supabase.table("court_rules").upsert(rows[i:i + 100], on_conflict="citation").execute()
print(f"UPSERTED {len(rows)} criminal rules.")
