#!/usr/bin/env python3
"""Phase 4 — Recover rejected forms by re-extracting text from PDFs.

Two sources:
  1. Supabase Storage bucket (rows with bucket_path) — download, extract.
  2. VPS harvest downloads (rows without bucket_path) — fuzzy name match,
     copy via local filesystem (this script runs ON the VPS where both the
     repo and /home/hermes/workspace/legal-clear live).

A row recovers when extraction yields >100 chars of text. Recovered rows get
form_text + a DeepSeek plain_language_summary and flip to published.
Rows with no extractable source get review_reason='no source PDF available'
and stay rejected.

Usage (VPS):
  cd backend && uv run python3 ../scripts/recover_rejected_forms.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import fitz  # pymupdf
import httpx

from src.memory.db import DatabaseManager  # noqa: E402

VPS_DOWNLOADS = Path("/home/hermes/workspace/legal-clear/forms-harvest/data/downloads")
RECOVERY_CSV = Path(__file__).resolve().parent / "forms_recovery.csv"
BUCKET = "court-forms"
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

_SUMMARY_PROMPT = (
    "Write a plain-English 2-3 sentence summary of this Florida court form "
    "for a self-represented (pro se) litigant. Explain what the form is, who "
    "files it, and when. No legal advice. No markdown.\n\nForm text excerpt:\n"
)


def extract_text_from_pdf_bytes(data: bytes) -> str:
    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def deepseek_summary(text: str) -> str:
    if not DEEPSEEK_KEY:
        return ""
    try:
        r = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": _SUMMARY_PROMPT + text[:6000]}
                ],
                "max_tokens": 200,
                "temperature": 0.3,
            },
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  deepseek summary failed: {e}")
    return ""


def fuzzy_match_vps(form_number: str) -> Path | None:
    """Match a rejected row's form_number to a VPS download file."""
    slug = re.sub(r"[^a-z0-9]+", "-", form_number.lower()).strip("-")
    slug = slug.replace("county-", "")
    # Direct filename candidates
    candidates = sorted(VPS_DOWNLOADS.glob("*.pdf"))
    for c in candidates:
        cname = c.name.lower().removesuffix(".pdf")
        if cname in slug or slug in cname:
            return c
    return None


def main() -> None:
    db = DatabaseManager()

    r = db.client.table("court_forms").select(
        "id,form_number,title,bucket_path,category"
    ).eq("status", "rejected").execute()
    rows = r.data or []
    print(f"Rejected rows to attempt: {len(rows)}")

    recovered = []
    still_rejected = []
    attempted = 0

    for row in rows:
        row_id = row["id"]
        fn = row["form_number"]
        pdf_bytes: bytes | None = None
        source = ""

        # Source 1: Supabase bucket
        if row.get("bucket_path"):
            try:
                pdf_bytes = db.client.storage.from_(BUCKET).download(row["bucket_path"])
                source = "supabase"
            except Exception as e:
                print(f"  bucket download failed for {fn}: {str(e)[:60]}")

        # Source 2: VPS downloads
        if pdf_bytes is None:
            match = fuzzy_match_vps(fn)
            if match:
                try:
                    pdf_bytes = match.read_bytes()
                    source = f"vps:{match.name}"
                except Exception as e:
                    print(f"  vps read failed for {fn}: {str(e)[:60]}")

        if pdf_bytes is None:
            db.client.table("court_forms").update({
                "review_reason": "no source PDF available for extraction",
            }).eq("id", row_id).execute()
            still_rejected.append({**row, "outcome": "no_source_pdf"})
            continue

        attempted += 1
        try:
            text = extract_text_from_pdf_bytes(pdf_bytes).strip()
        except Exception as e:
            print(f"  extraction failed for {fn}: {str(e)[:60]}")
            still_rejected.append({**row, "outcome": f"extract_failed: {str(e)[:40]}"})
            continue

        if len(text) <= 100:
            db.client.table("court_forms").update({
                "review_reason": "PDF is image-only (no text layer) — needs OCR",
            }).eq("id", row_id).execute()
            still_rejected.append({**row, "outcome": "no_text_layer"})
            continue

        # Recovered! Write form_text + summary, publish.
        summary = deepseek_summary(text)
        db.client.table("court_forms").update({
            "form_text": text[:100000],
            "plain_language_summary": summary or None,
            "status": "published",
            "review_reason": None,
        }).eq("id", row_id).execute()
        recovered.append({**row, "outcome": "recovered", "chars": len(text), "source": source})
        print(f"  RECOVERED {fn} ({len(text)} chars, source={source})")

    # Write recovery CSV
    with open(RECOVERY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "form_number", "title", "category",
                           "outcome", "chars", "source"]
        )
        writer.writeheader()
        for rw in recovered:
            writer.writerow({k: rw.get(k, "") for k in writer.fieldnames})
        for rw in still_rejected:
            writer.writerow({k: rw.get(k, "") for k in writer.fieldnames})

    print(f"\nAttempted: {attempted}")
    print(f"Recovered: {len(recovered)}")
    print(f"Still rejected: {len(still_rejected)}")
    print(f"CSV: {RECOVERY_CSV}")


if __name__ == "__main__":
    main()
