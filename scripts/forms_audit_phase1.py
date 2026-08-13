#!/usr/bin/env python3
"""
Phase 1 — Forms Catalog Audit (read-only).

Classify every row in Supabase court_forms into exactly one target_area:
  filing     — form filed with the court to start/respond/advance a case
  payment    — credit card/fine/payment/fee clerk forms (NOT filing forms)
  redaction  — SSN/bank account redaction request forms (supporting)
  uncertain  — cannot determine from title/summary

Deterministic keyword rules only — no LLM. Writes forms_audit.csv.

Usage:
  cd backend && uv run python3 ../scripts/forms_audit_phase1.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from src.memory.db import DatabaseManager  # noqa: E402

OUT_CSV = Path(__file__).resolve().parent / "forms_audit.csv"

# ── Keyword rules ──────────────────────────────────────────────────────────────
# clerk_admin = pure clerk's-office transaction forms (fee schedules, credit card
# forms) — NOT case filings, should leave the filing catalog.
CLERK_ADMIN_PATTERNS = [
    r"fee schedule", r"credit card", r"fax", r"checkout", r"cashier",
    r"payment form\b", r"payment authorization", r"pay[- ]?online",
    r"electronic payment", r"payment stub",
    r"schedule of fees", r"budget", r"level of service", r"appropriation",
    r"marriage license", r"official records", r"change of address",
    r"financial report", r"audit report",
]
# redaction = privacy forms (SSN removal). Filed with clerk, but not case-filing.
REDACTION_PATTERNS = [
    r"redact", r"ssn", r"social security number", r"account number",
    r"removal of.*number", r"confidential.*number", r"internet document removal",
]
# Everything that is a court document = filing. The FL Supreme Court 12.9xx
# family law series is ALL filing forms.
FILING_STRONG = [
    r"petition", r"motion", r"complaint", r"answer", r"notice of",
    r"affidavit", r"summons", r"judgment", r"order to show", r"response",
    r"counterclaim", r"stipulation", r"waiver", r"certificate", r"request for",
    r"application", r"statement of claim", r"writ", r"subpoena", r"discovery",
    r"interrogator", r"request to produce", r"admission",
    r"injunction", r"custody", r"dissolution", r"divorce", r"eviction",
    r"small claims", r"guardian", r"probate", r"adoption", r"name change",
    r"parenting plan", r"support", r"modification", r"contempt",
    r"restraining", r"protection", r"appeal", r"rehearing",
    r"settlement agreement", r"termination of", r"appearance", r"exemption",
    r"withholding order", r"garnishment", r"installment", r"payment plan",
    r"payment credit", r"tax deed", r"surplus proceeds", r"agreement",
    r"order", r"verification", r"checklist", r"information", r"instruction",
]


def classify(title: str, summary: str, category: str, form_number: str) -> tuple[str, str, str]:
    """Return (target_area, confidence, reason)."""
    text = f"{title} {summary} {form_number}".lower()
    fn = form_number.lower()

    # Clerk's-office transaction forms — most specific junk, out first
    for pat in CLERK_ADMIN_PATTERNS:
        if re.search(pat, text):
            return "clerk_admin", "high", f"clerk transaction pattern: {pat}"

    # Redaction/privacy forms
    for pat in REDACTION_PATTERNS:
        if re.search(pat, text):
            return "redaction", "high", f"redaction pattern: {pat}"

    # FL Supreme Court form series — 12.9xx are all family law filing forms
    if re.match(r"^12\.9\d\d", fn):
        return "filing", "high", "FL Supreme Court family law form series (12.9xx)"

    # Strong filing signals
    strong_hits = [p for p in FILING_STRONG if re.search(p, text)]
    if strong_hits:
        return "filing", "high", f"filing signal: {strong_hits[0]}"

    # Weak/unknown → uncertain
    return "uncertain", "low", "no filing/payment/redaction signal in metadata"


def main() -> None:
    db = DatabaseManager()

    print("Fetching all court_forms rows...")
    rows: list[dict] = []
    offset = 0
    while True:
        r = (
            db.client.table("court_forms")
            .select("id, form_number, title, category, status, plain_language_summary, source_page_url")
            .order("form_number")
            .range(offset, offset + 999)
            .execute()
        )
        if not r.data:
            break
        rows.extend(r.data)
        offset += 1000

    print(f"  {len(rows)} rows fetched")

    # Classify
    audit_rows = []
    counts: dict[str, int] = {}
    for row in rows:
        area, conf, reason = classify(
            row.get("title") or "",
            row.get("plain_language_summary") or "",
            row.get("category") or "",
            row.get("form_number") or "",
        )
        counts[area] = counts.get(area, 0) + 1
        audit_rows.append({
            "id": row["id"],
            "form_number": row.get("form_number") or "",
            "title": (row.get("title") or "")[:120],
            "current_category": row.get("category") or "",
            "current_status": row.get("status") or "",
            "target_area": area,
            "confidence": conf,
            "reason": reason,
        })

    # Write CSV
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "form_number", "title", "current_category",
                        "current_status", "target_area", "confidence", "reason"],
        )
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"\nWrote {len(audit_rows)} rows to {OUT_CSV}")
    print("\nCounts per target_area:")
    for area in ("filing", "clerk_admin", "redaction", "uncertain"):
        print(f"  {area}: {counts.get(area, 0)}")

    print("\nSample clerk_admin rows:")
    for a in audit_rows:
        if a["target_area"] == "clerk_admin":
            print(f"  {a['form_number'][:50]} | {a['title'][:70]}")

    print("\nSample redaction rows:")
    for a in audit_rows:
        if a["target_area"] == "redaction":
            print(f"  {a['form_number'][:50]} | {a['title'][:70]}")

    print("\nSample uncertain rows:")
    n = 0
    for a in audit_rows:
        if a["target_area"] == "uncertain":
            print(f"  {a['form_number'][:50]} | {a['title'][:70]}")
            n += 1
            if n >= 10:
                break


if __name__ == "__main__":
    main()
