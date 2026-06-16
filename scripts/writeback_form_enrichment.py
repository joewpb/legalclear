#!/usr/bin/env python3
"""Phase 10 — writeback of LLM enrichment into court_forms.

Consumes the cheap enrichment agent's output and writes plain_language_summary
+ situation_tags back onto each form by form_number. Deterministic; no LLM.

Expected input JSON (array):
    [
      {
        "form_number": "12.901(b)(1)",
        "plain_language_summary": "Use this form to start a divorce when ...",
        "situation_tags": ["divorce", "minor_children", "petitioner"]
      },
      ...
    ]

Run from repo root:
    cd backend
    uv run python ../scripts/writeback_form_enrichment.py ../forms/enrichment_output.json            # dry-run
    uv run python ../scripts/writeback_form_enrichment.py ../forms/enrichment_output.json --execute   # write DB

DO NOT run until the enrichment agent has produced its output file.
Requires backend/.env with SUPABASE_URL + SUPABASE_SERVICE_KEY (for --execute).
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_env():
    env = REPO / "backend" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def validate(records):
    ok, bad = [], []
    for i, r in enumerate(records):
        fn = (r.get("form_number") or "").strip()
        summary = r.get("plain_language_summary")
        tags = r.get("situation_tags")
        if not fn:
            bad.append((i, "missing form_number")); continue
        if not isinstance(summary, str) or not summary.strip():
            bad.append((i, f"{fn}: empty plain_language_summary")); continue
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            bad.append((i, f"{fn}: situation_tags must be a string list")); continue
        rec = {
            "form_number": fn,
            "plain_language_summary": summary.strip(),
            "situation_tags": [t.strip() for t in tags if t.strip()],
        }
        # Optional corrected title (for forms flagged needs_title at ingest).
        title = r.get("title")
        if isinstance(title, str) and title.strip():
            rec["title"] = title.strip()[:500]
        ok.append(rec)
    return ok, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="path to the enrichment agent's output JSON")
    ap.add_argument("--execute", action="store_true", help="write to court_forms (default: validate only)")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        sys.exit(f"input not found: {path}")
    records = json.loads(path.read_text())
    if not isinstance(records, list):
        sys.exit("input must be a JSON array")

    ok, bad = validate(records)
    print(f"valid: {len(ok)}  |  rejected: {len(bad)}")
    for i, why in bad[:50]:
        print(f"  reject[{i}]: {why}")

    if not args.execute:
        print("\n(validate-only — re-run with --execute to write DB.)")
        return
    if not ok:
        sys.exit("nothing valid to write.")

    load_env()
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in backend/.env")
    from supabase import create_client
    client = create_client(url, key)

    updated = failed = 0
    for r in ok:
        payload = {
            "plain_language_summary": r["plain_language_summary"],
            "situation_tags": r["situation_tags"],
            "updated_at": "now()",
        }
        if "title" in r:
            payload["title"] = r["title"]
        try:
            res = client.table("court_forms").update(
                payload
            ).eq("form_number", r["form_number"]).execute()
            if res.data:
                updated += 1
            else:
                failed += 1
                print(f"  ! no row for form_number {r['form_number']}")
        except Exception as ex:
            failed += 1
            print(f"  ! update failed {r['form_number']}: {ex}")
    print(f"\nupdated: {updated}  |  failed: {failed}")


if __name__ == "__main__":
    main()
