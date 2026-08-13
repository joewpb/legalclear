#!/usr/bin/env python3
"""Phase 2 — Recategorize court_forms based on the approved audit CSV.

- clerk_admin rows → category='clerk_administrative', status='review'
- redaction rows  → category='clerk_administrative', status='review'
- uncertain rows  → status='review' (keep category)
- filing rows     → untouched

Reports counts before/after. Nothing is deleted.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from src.memory.db import DatabaseManager  # noqa: E402

AUDIT_CSV = Path(__file__).resolve().parent / "forms_audit.csv"


def main() -> None:
    db = DatabaseManager()

    # Published count before
    r0 = db.client.table("court_forms").select("id", count="exact").eq("status", "published").execute()
    print(f"Published BEFORE: {r0.count}")

    # Load audit CSV
    clerk_admin = []
    redaction = []
    uncertain = []
    with open(AUDIT_CSV) as f:
        for row in csv.DictReader(f):
            if row["target_area"] == "clerk_admin":
                clerk_admin.append(row)
            elif row["target_area"] == "redaction":
                redaction.append(row)
            elif row["target_area"] == "uncertain":
                uncertain.append(row)

    print(f"\nTo move:")
    print(f"  clerk_admin → clerk_administrative + review: {len(clerk_admin)}")
    print(f"  redaction   → clerk_administrative + review: {len(redaction)}")
    print(f"  uncertain   → review (category kept): {len(uncertain)}")

    # Apply updates
    moved = 0
    failed = 0

    for row in clerk_admin:
        r = (
            db.client.table("court_forms")
            .update({
                "category": "clerk_administrative",
                "status": "review",
                "review_reason": f"clerk_admin: moved out of filing catalog ({row['reason'][:80]})",
            })
            .eq("id", row["id"])
            .execute()
        )
        if r.data is not None:
            moved += 1
        else:
            failed += 1

    for row in redaction:
        r = (
            db.client.table("court_forms")
            .update({
                "category": "clerk_administrative",
                "status": "review",
                "review_reason": f"redaction: moved out of filing catalog ({row['reason'][:80]})",
            })
            .eq("id", row["id"])
            .execute()
        )
        if r.data is not None:
            moved += 1
        else:
            failed += 1

    for row in uncertain:
        r = (
            db.client.table("court_forms")
            .update({
                "status": "review",
                "review_reason": f"form audit: category uncertain ({row['reason'][:80]})",
            })
            .eq("id", row["id"])
            .execute()
        )
        if r.data is not None:
            moved += 1
        else:
            failed += 1

    print(f"\nRows updated: {moved}")
    print(f"Failed: {failed}")

    # Verify
    r1 = db.client.table("court_forms").select("id", count="exact").eq("status", "published").execute()
    r2 = db.client.table("court_forms").select("id", count="exact").eq("category", "clerk_administrative").eq("status", "published").execute()
    r3 = db.client.table("court_forms").select("id", count="exact").eq("status", "review").execute()

    print(f"\nPublished AFTER: {r1.count}")
    print(f"Published clerk_administrative (must be 0): {r2.count}")
    print(f"Review status: {r3.count}")


if __name__ == "__main__":
    main()
