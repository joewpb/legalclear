#!/usr/bin/env python3
"""Load the 636-chapter Orin statutes harvest into Supabase.

Semantics (per Joe's ruling — pure addition, nothing overwritten):
  - citation ABSENT in prod        -> insert
  - citation present, prod text is STUB (< 200 chars) -> replace with Orin's verified text
  - citation present, prod text is REAL (>= 200)       -> keep prod row (verified)
Report per-category counts + named failures. Nothing else written.
"""
import json
import os
import sys
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

STAGE = Path("/tmp/orin_statutes")
STUB_THRESHOLD = 200
BATCH = 200

def main() -> None:
    from supabase import create_client

    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(url, key)

    # existing citations + current text lengths
    prod: dict[str, int] = {}
    offset = 0
    while True:
        resp = supabase.table("statutes").select("citation,text").range(offset, offset + 9999).execute()
        rows = resp.data or []
        if not rows:
            break
        for r in rows:
            prod[r["citation"]] = len(r.get("text") or "")
        offset += len(rows)
    print(f"prod statutes before load: {len(prod)}")

    files = sorted(STAGE.glob("statutes_*.jsonl"))
    to_insert: list[dict] = []
    to_replace: list[dict] = []
    skipped_real: int = 0
    failures: list[str] = []
    seen: set[str] = set()

    for f in files:
        try:
            for line in f.read_text().splitlines():
                r = json.loads(line)
                cite = r.get("citation")
                if not cite:
                    failures.append(f"{f.name}: row missing citation")
                    continue
                if cite in seen:
                    continue
                seen.add(cite)
                text = r.get("text") or ""
                row = {
                    "citation": cite,
                    "chapter": r.get("chapter"),
                    "section": r.get("section"),
                    "subsection": r.get("subsection"),
                    "text": text,
                    "source_url": r.get("source_url"),
                    "jurisdiction": "FL",
                }
                cur_len = prod.get(cite)
                if cur_len is None:
                    to_insert.append(row)
                elif cur_len < STUB_THRESHOLD:
                    to_replace.append(row)
                else:
                    skipped_real += 1
        except Exception as e:  # noqa: BLE001
            failures.append(f"{f.name}: {type(e).__name__}: {e}")

    def push(rows: list[dict], label: str) -> None:
        n = 0
        for i in range(0, len(rows), BATCH):
            supabase.table("statutes").upsert(rows[i:i + BATCH], on_conflict="citation").execute()
            n += len(rows[i:i + BATCH])
        print(f"{label}: {n}")

    push(to_insert, "inserted (new citations)")
    push(to_replace, "replaced (stub rows -> verified text)")
    print(f"kept prod rows with real text: {skipped_real}")
    print(f"failures: {len(failures)}")
    for x in failures[:30]:
        print(f"  FAIL: {x}")

    # post-load count
    resp = supabase.table("statutes").select("citation", count="exact").limit(1).execute()
    print(f"prod statutes after load: {resp.count if hasattr(resp, 'count') else '?'}")

if __name__ == "__main__":
    main()
