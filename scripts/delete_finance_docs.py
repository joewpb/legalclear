#!/usr/bin/env python3
"""Delete county financial documents (budget books, fee schedules, CIP, etc.)
from Supabase court_forms. Reads the Phase 1 audit CSV, selects rows whose
title matches finance-document patterns, deletes them by id.

Deterministic — only rows matching the finance patterns are deleted.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from src.memory.db import DatabaseManager  # noqa: E402

AUDIT_CSV = Path(__file__).resolve().parent / "forms_audit.csv"

# County finance documents — NOT court forms, harvested by accident.
FINANCE_PATTERNS = [
    r"budget", r"fee schedule", r"schedule of fees", r"service charges",
    r"service fee charges", r"cip\b", r"capital improvement", r"millage",
    r"level of service", r"county manager", r"single source", r"sole source",
    r"strategic plan", r"carryforward", r"capital budget", r"adopted budget",
    r"tentative budget", r"amended budget", r"budget amendment",
]


def is_finance_doc(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in FINANCE_PATTERNS)


def main() -> None:
    db = DatabaseManager()

    # Load audit CSV
    targets = []
    with open(AUDIT_CSV) as f:
        for row in csv.DictReader(f):
            if is_finance_doc(row["title"]):
                targets.append(row)

    print(f"Finance documents to delete: {len(targets)}")

    # Show them
    for t in targets:
        print(f"  {t['form_number'][:55]} | {t['title'][:65]} | status={t['current_status']}")

    # Delete
    deleted = 0
    failed = 0
    for t in targets:
        r = db.client.table("court_forms").delete().eq("id", t["id"]).execute()
        if r.data or getattr(r, "count", None) is not None:
            deleted += 1
        else:
            failed += 1

    print(f"\nDeleted: {deleted}")
    print(f"Failed: {failed}")

    # Verify
    r2 = db.client.table("court_forms").select("id", count="exact").execute()
    print(f"\nRemaining rows in court_forms: {r2.count}")


if __name__ == "__main__":
    main()
