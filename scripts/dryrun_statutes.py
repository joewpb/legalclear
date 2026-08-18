#!/usr/bin/env python3
"""Dry-run: fetch ch.83 + ch.34 chapter pages, parse with the fixed parser,
print per-section body lengths. No DB writes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx
from ingest_statutes import fetch_chapter_html, parse_chapter_html, validate_record

with httpx.Client(timeout=90, follow_redirects=True) as client:
    for ch in ("83", "34"):
        print(f"=== Chapter {ch} ===", flush=True)
        html_str = fetch_chapter_html(ch, client)
        if html_str is None:
            print("FETCH FAILED")
            continue
        records = parse_chapter_html(html_str, ch)
        by_cite = {}
        for r in records:
            c = r["citation"]
            if c not in by_cite or len(r["text"]) > len(by_cite[c]["text"]):
                by_cite[c] = r
        recs = list(by_cite.values())
        print(f"parsed {len(records)} raw / {len(recs)} deduped sections")
        ok_count = 0
        for r in recs:
            ok, reason = validate_record(r)
            flag = "OK " if ok else "FAIL"
            if ok:
                ok_count += 1
            print(f"  {flag} {r['citation']}: total={len(r['text'])} {reason} | title={r['title'][:40]}")
        print(f"  → {ok_count}/{len(recs)} pass validation")
        print()
