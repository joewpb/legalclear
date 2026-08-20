#!/usr/bin/env python3
"""Second pass on the kept rows: detect TOC-junk text (dotted leader + page
number) and, where the existing text is TOC junk or a partial, update with the
official span text even when shorter. Also retry 3.214 with fragment-join."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_criminal_from_cache import candidates  # noqa: E402

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

CACHE = Path.home() / ".hermes/cache/web/www-media.floridabar.org-36c69b54db.md"
raw = CACHE.read_text()
hdr = re.compile(r"RULE\s+(3\.\d+(?:\.\d+)*)\s*\.?", re.IGNORECASE)
positions = [(m.start(), m.end(), m.group(1)) for m in hdr.finditer(raw)]


def span_text(num):
    for i, (start, end, n) in enumerate(positions):
        if n != num:
            continue
        j = i + 1
        while j < len(positions) and positions[j][2] == num:
            j += 1
        block = raw[end:positions[j][0]] if j < len(positions) else raw[end:]
        block = re.sub(r"Florida Rules of Criminal Procedure\s*\w+\s+\d+,?\s*\d*\s*\d+", " ", block)
        block = re.sub(r"\s+", " ", block).strip()
        return block
    return ""


def joined_text(num):
    frags = candidates.get(num, [])
    if len(frags) > 1:
        return re.sub(r"\s+", " ", " ".join(frags[1:])).strip()
    return re.sub(r"\s+", " ", (frags[0] if frags else "")).strip()


TOC_JUNK = re.compile(r"\.{4,}\s*\d+")

rows = json.loads(open("/tmp/rules_audit.json").read())
kept = {r["rule_number"]: r for r in rows if r["rule_number"] in ("3.214", "3.990", "3.991", "3.992")}

from supabase import create_client  # noqa: E402

supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])

for n, r in sorted(kept.items()):
    existing = (r["text"] or "").strip()
    span = span_text(n)
    joined = joined_text(n)
    is_toc = bool(TOC_JUNK.search(existing))
    print(f"{n}: existing={len(existing)} toc_junk={is_toc} | span={len(span)} | joined={len(joined)}")
    print(f"   existing head: {existing[:90]!r}")
    print(f"   span head:    {span[:90]!r}")
    # choose: prefer span if existing is TOC junk or much shorter; prefer joined if substantially longer and not TOC
    choice = None
    if is_toc:
        choice = span
    elif len(joined) > 3 * len(existing) and not TOC_JUNK.search(joined):
        choice = joined
    elif len(span) > len(existing) * 1.2:
        choice = span
    if choice:
        supabase.table("court_rules").update({"text": choice}).eq("rule_set", r["rule_set"]).eq("rule_number", n).execute()
        print(f"   -> UPDATED {len(existing)} -> {len(choice)}")
    else:
        print("   -> LEFT AS-IS (named)")
