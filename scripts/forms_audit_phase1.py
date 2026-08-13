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

# ── Keyword rules (layered, title-first) ────────────────────────────────────────
# HARD junk — never filing forms. Checked against TITLE only, first.
HARD_JUNK = [
    r"fee schedule", r"credit card", r"fax", r"checkout", r"cashier",
    r"payment form\b", r"payment authorization", r"pay[- ]?online",
    r"electronic payment", r"payment stub",
    r"schedule of fees", r"budget", r"level of service", r"appropriation",
    r"marriage license", r"official records", r"financial report",
    r"audit report", r"county manager", r"millage", r"\bcip\b",
    r"source report", r"strategic plan", r"assessment", r"amendment",
    r"ordinance", r"holiday schedule", r"workshop", r"brochure",
    r"memo\b", r"registry of court open cases", r"imaging",
    r"department of highway safety", r"dhsmv", r"traffic memo",
]
# redaction = privacy forms (SSN removal). Title check.
REDACTION_PATTERNS = [
    r"redact", r"ssn", r"social security number", r"account number",
    r"removal of.*number", r"confidential.*number", r"internet document removal",
    r"\bacct", r"exempt personal information", r"release.*redacted",
]
# Category signal — if the DB category already says what kind of legal form
# this is, trust it. These are LegalClear's curated categories, all filing.
FILING_CATEGORIES = {
    "small_claims", "eviction", "domestic_violence", "family_law",
    "family_law_support", "family_law_children", "family_law_contempt",
    "family_law_dissolution", "family_law_enforcement", "family_law_financial",
    "family_law_misc", "family_law_modification", "family_law_procedure",
    "name_change", "probate_estate", "guardianship", "criminal", "traffic",
    "civil", "civil_rights",
}

# STRONG filing words in the TITLE — unambiguously court filings.
STRONG_FILING_TITLE = [
    r"petition", r"motion", r"complaint", r"answer", r"affidavit",
    r"notice of", r"writ", r"subpoena", r"judgment", r"stipulation",
    r"settlement agreement", r"order to show", r"designation of",
    r"termination of", r"exemption", r"withholding", r"garnishment",
    r"installment", r"payment plan", r"payment credit", r"tax deed",
    r"surplus proceeds", r"counterclaim", r"response to", r"summons",
    r"claim of", r"injunction", r"custody", r"dissolution", r"divorce",
    r"eviction", r"small claims", r"guardian", r"probate", r"adoption",
    r"name change", r"parenting plan", r"support", r"modification",
    r"contempt", r"restraining", r"protection", r"appeal", r"rehearing",
    r"statement of claim", r"notice of hearing", r"motion for", r"request to",
    r"order granting", r"order denying", r"final judgment", r"consent",
    r"waiver of", r"acceptance of service", r"\bpet\b", r"\bmtn\b",
    r"administrative order", r"\bao\b", r"standing order",
]
# WEAKER filing signals — checked against title+summary combined.
FILING_WEAK = [
    r"agreement", r"verification", r"checklist", r"instruction",
    r"information sheet", r"order\b", r"request for", r"application",
    r"discovery", r"interrogator", r"appearance",
]
# SOFT admin — clerk-side patterns, checked against title+summary LAST.
SOFT_ADMIN = [
    r"change of address", r"payment authorization", r"payment form",
    r"unclaimed funds", r"request copies", r"request for removal",
]


def classify(title: str, summary: str, category: str, form_number: str) -> tuple[str, str, str]:
    """Return (target_area, confidence, reason). Layered: hard junk → redaction
    → strong filing title → form series → weak filing → soft admin."""
    title_l = title.lower()
    text = f"{title} {summary}".lower()
    fn = form_number.lower()

    # 1. HARD junk (title only — never a filing form)
    for pat in HARD_JUNK:
        if re.search(pat, title_l):
            return "clerk_admin", "high", f"title junk pattern: {pat}"

    # 2. Redaction/privacy (title only)
    for pat in REDACTION_PATTERNS:
        if re.search(pat, title_l):
            return "redaction", "high", f"redaction pattern: {pat}"

    # 3. Strong filing words in title — unambiguous court filings win
    strong_hits = [p for p in STRONG_FILING_TITLE if re.search(p, title_l)]
    if strong_hits:
        return "filing", "high", f"filing title signal: {strong_hits[0]}"

    # 4. FL Supreme Court form series — 12.9xx are all family law filing forms
    if re.match(r"^12\.9\d\d", fn):
        return "filing", "high", "FL Supreme Court family law form series (12.9xx)"

    # 4b. DB category signal — curated categories are all filing forms
    if category in FILING_CATEGORIES:
        return "filing", "high", f"db category signal: {category}"

    # 5. Weaker signals in title+summary
    weak_hits = [p for p in FILING_WEAK if re.search(p, text)]
    if weak_hits:
        return "filing", "low", f"weak filing signal: {weak_hits[0]}"

    # 6. Soft admin patterns (title+summary)
    for pat in SOFT_ADMIN:
        if re.search(pat, text):
            return "clerk_admin", "low", f"soft admin pattern: {pat}"

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
