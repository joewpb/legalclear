#!/usr/bin/env python3
"""Re-apply pass-1 span updates for 3.505/3.250/3.260/3.270 (clobbered by the
harvest-cache import side effect)."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    best = ""
    for i, (start, end, n) in enumerate(positions):
        if n != num:
            continue
        j = i + 1
        while j < len(positions) and positions[j][2] == num:
            j += 1
        block = raw[end:positions[j][0]] if j < len(positions) else raw[end:]
        block = re.sub(r"Florida Rules of Criminal Procedure\s*\w+\s+\d+,?\s*\d*\s*\d+", " ", block)
        block = re.sub(r"\s+", " ", block).strip()
        if len(block) > len(best):
            best = block
    return best


from supabase import create_client  # noqa: E402

supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])
rows = json.loads(open("/tmp/rules_audit.json").read())
for n in ("3.505", "3.250", "3.260", "3.270"):
    r = [x for x in rows if x["rule_number"] == n][0]
    t = span_text(n)
    before = len(r["text"] or "")
    if t and len(t) > before:
        supabase.table("court_rules").update({"text": t}).eq("rule_set", "criminal").eq("rule_number", n).execute()
        print(f"{n}: re-applied {before} -> {len(t)}")
    else:
        print(f"{n}: span still short ({len(t)}), left as-is")
