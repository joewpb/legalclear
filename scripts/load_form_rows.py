#!/usr/bin/env python3
"""Route Orin's 30 FORM rows to court_forms (Job 3).

Mapping: citation number -> form_number; title with FORM prefix stripped ->
title; text -> form_text; source_url -> source_page_url. Missing fields get
explicit harvested-not-curated defaults (status='review',
review_reason='harvested from official rules PDF 2026-08-20; not yet curated',
category by set, situation_tags=[]). Existing form_numbers are skipped
(ON CONFLICT DO NOTHING semantics, done client-side)."""
import json
import os
import re
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
for line in env_path.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

SET_CATEGORY = {
    "rules_small_claims": "small_claims",
    "rules_general_practice": "general_practice",
}


def main() -> None:
    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"])

    forms = []
    for name, category in SET_CATEGORY.items():
        for line in open(f"/tmp/orin_stage/{name}.jsonl"):
            r = json.loads(line)
            text = (r.get("text") or "").strip()
            if not text.upper().startswith("FORM"):
                continue
            num = r["rule_number"]
            title = text.split("\n")[0].strip()
            title = re.sub(r"^FORM\s+" + re.escape(num) + r"\.\s*", "", title, flags=re.IGNORECASE).strip()
            forms.append({
                "form_number": num,
                "title": title,
                "form_text": text,
                "source_page_url": r.get("source_url"),
                "category": category,
                "status": "review",
                "review_reason": "harvested from official rules PDF 2026-08-20; not yet curated",
                "situation_tags": [],
            })
    print(f"FORM rows to route: {len(forms)}")

    existing = set()
    offset = 0
    while True:
        resp = supabase.table("court_forms").select("form_number").range(offset, offset + 9999).execute()
        rows = resp.data or []
        if not rows:
            break
        existing.update(r["form_number"] for r in rows if r.get("form_number"))
        offset += len(rows)
    print(f"court_forms rows before: {len(existing)}")

    new_forms = [f for f in forms if f["form_number"] not in existing]
    skipped = len(forms) - len(new_forms)
    inserted = 0
    failed = []
    for i in range(0, len(new_forms), 20):
        batch = new_forms[i:i + 20]
        try:
            supabase.table("court_forms").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:  # noqa: BLE001
            failed.append(str(e))

    print(f"inserted: {inserted} | skipped (existing form_number): {skipped} | failed: {len(failed)}")
    for f in failed[:5]:
        print(f"  {f}")

    resp = supabase.table("court_forms").select("form_number", count="exact").limit(1).execute()
    print(f"court_forms rows after: {resp.count if hasattr(resp, 'count') else '?'}")


if __name__ == "__main__":
    main()
