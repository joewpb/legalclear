#!/usr/bin/env python3
"""Harvest Florida court-rule PDFs into court_rules (Job 1, 2026-08-18).

Scope: 2.514 (gen prac) | 7.x full (small claims) | 3.x full (criminal) |
1.280–1.400 (civil procedure discovery range). Same validation discipline as
the statute rebuild: body detection + min-length report + spot verification;
fetch -> validate -> replace per rule; failures named individually.

Source: The Florida Bar official rule PDFs (current 2026 editions).
"""
import argparse
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import fitz  # pymupdf

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

MIN_BODY_CHARS = 120

TARGETS = [
    {
        "rule_set": "general_practice",
        "prefix": "Fla. R. Gen. Prac. & Jud. Admin.",
        "url": "https://www-media.floridabar.org/uploads/2026/07/2027_01-JULY-Florida-Rules-of-General-Practice-and-Judicial-Administration-7-1-2026-1.pdf",
        "mode": "exact",
        "numbers": {"2.514"},
    },
    {
        "rule_set": "small_claims",
        "prefix": "Fla. Sm. Cl. R.",
        "url": "https://www-media.floridabar.org/uploads/2026/08/2026_01-JUL-Small-Claims-Rules-7-1-2026-1.pdf",
        "mode": "all",
        "numbers": None,
    },
    {
        "rule_set": "criminal",
        "prefix": "Fla. R. Crim. P.",
        "url": "https://www-media.floridabar.org/uploads/2026/07/2026_01-JUL-Criminal-Procedure-Rules-7-13-2026-1.pdf",
        "mode": "all",
        "numbers": None,
    },
    {
        "rule_set": "civil_procedure",
        "prefix": "Fla. R. Civ. P.",
        "url": "https://www-media.floridabar.org/uploads/2026/04/Civil-Procedure-Rules-04-01-26.pdf",
        "mode": "range",
        "numbers": ("1.280", "1.400"),
    },
]

RULE_HDR_RE = re.compile(r"^\s*RULE\s+(\d+\.\d+)\s*[.\u2014\u2013:-]\s*(.*)$", re.IGNORECASE)


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "application/pdf,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    time.sleep(1.2)


def extract_rules(pdf_path: Path) -> list[tuple[str, str, str]]:
    """Return [(rule_number, title, body_text)] parsed from the PDF.

    The PDFs open with a table of contents whose entries also start with
    "RULE X.Y." — for each rule number we keep the LONGEST captured block
    (the body section), which defeats the TOC.
    """
    doc = fitz.open(str(pdf_path))
    lines: list[str] = []
    for page in doc:
        lines.extend(page.get_text("text").splitlines())
    doc.close()

    candidates: dict[str, list[tuple[str, str]]] = {}
    cur_num: str | None = None
    cur_title: str | None = None
    buf: list[str] = []
    for line in lines:
        m = RULE_HDR_RE.match(line.strip())
        if m:
            if cur_num is not None:
                candidates.setdefault(cur_num, []).append((cur_title or "", "\n".join(buf).strip()))
            cur_num, cur_title = m.group(1), m.group(2).strip()
            buf = []
            continue
        if cur_num is not None:
            buf.append(line)
    if cur_num is not None:
        candidates.setdefault(cur_num, []).append((cur_title or "", "\n".join(buf).strip()))

    rules: list[tuple[str, str, str]] = []
    for num in sorted(candidates, key=lambda n: tuple(int(x) for x in n.split("."))):
        best = max(candidates[num], key=lambda tb: len(tb[1]))
        body = best[1]
        # strip per-page headers/footers ("Page N of M", date line, rule-set name)
        body = re.sub(r"\n?(?:July|Jan|Oct|Apr)\s+\d{1,2},\s+202[0-9]\s*\n?", "\n", body)
        body = re.sub(r"\n?Page\s+\d+\s+of\s+\d+\s*\n?", "\n", body)
        body = re.sub(r"\n?Fla\.\s*R\.\s*(?:Gen\.\s*Prac\.\s*&\s*Jud\.\s*Admin\.|Sm\.\s*Cl\.|Crim\.\s*P\.|Civ\.\s*P\.)\s*\n?", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        rules.append((num, best[0], body))
    return rules


def in_scope(num: str, tgt: dict) -> bool:
    if tgt["mode"] == "all":
        return True
    if tgt["mode"] == "exact":
        return num in tgt["numbers"]
    lo, hi = tgt["numbers"]
    return lo <= num <= hi


def upsert(supabase, rows: list[dict]) -> None:
    if not rows:
        return
    for i in range(0, len(rows), 100):
        supabase.table("court_rules").upsert(rows[i:i + 100], on_conflict="citation").execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="extract + validate, no DB writes")
    args = parser.parse_args()

    supabase = None
    if not args.dry_run:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    staging = Path("/tmp/lc_rules_harvest")
    staging.mkdir(exist_ok=True)
    total_loaded = 0
    failures: list[str] = []

    for tgt in TARGETS:
        print(f"=== {tgt['rule_set']} ===", flush=True)
        pdf_path = staging / f"{tgt['rule_set']}.pdf"
        try:
            if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
                download(tgt["url"], pdf_path)
            text_rules = extract_rules(pdf_path)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{tgt['rule_set']}: FETCH/EXTRACT FAILED: {e}")
            print(f"  FAILED: {e}")
            continue

        scoped = [(n, t, b) for n, t, b in text_rules if in_scope(n, tgt)]
        print(f"  extracted {len(text_rules)} rules total; {len(scoped)} in scope")
        rows: list[dict] = []
        for num, title, body in scoped:
            body_len = len(body)
            if body_len < MIN_BODY_CHARS:
                failures.append(f"{tgt['rule_set']} {num}: body {body_len} chars < {MIN_BODY_CHARS}")
                print(f"  FAIL {num}: body {body_len} chars")
                continue
            rows.append({
                "citation": f"{tgt['prefix']} {num}",
                "rule_set": tgt["rule_set"],
                "rule_number": num,
                "subsection": None,
                "title": (title[:200] or None),
                "text": body,
                "source_url": tgt["url"],
                "jurisdiction": "FL",
            })
        if not args.dry_run and rows:
            upsert(supabase, rows)
        total_loaded += len(rows)
        print(f"  loaded {len(rows)} rules")
        for num, title, body in scoped:
            if len(body) < 200:
                print(f"  NOTE {num}: {len(body)} chars (short — verify)")

    print(f"\nDone. Loaded {total_loaded}. Failures: {len(failures)}")
    for f in failures:
        print(f"  FAIL: {f}")


if __name__ == "__main__":
    main()
