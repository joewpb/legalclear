#!/usr/bin/env python3
"""
Ingest Florida Court Rules from PDFs into Supabase court_rules table.

Usage:
    cd backend
    uv run python ../scripts/ingest_court_rules.py

Requirements:
    - PDFs must be in backend/src/data/rules/
    - PyMuPDF (fitz) for PDF parsing
    - Supabase credentials in backend/.env
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client
import fitz  # PyMuPDF

# Add OCR support
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
from ingestion.ocr import OCRProcessor

# Load environment
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Rule set configurations
RULE_SETS = {
    "general_practice": {
        "citation_prefix": "Fla. R. Gen. Prac. & Jud. Admin.",
        "name": "General Practice & Judicial Administration",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-General-Practice-and-Judicial-Administration"
    },
    "civil_procedure": {
        "citation_prefix": "Fla. R. Civ. P.",
        "name": "Civil Procedure",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-Civil-Procedure"
    },
    "small_claims": {
        "citation_prefix": "Fla. Sm. Cl. R.",
        "name": "Small Claims Rules",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Small-Claims-Rules"
    },
    "family_law": {
        "citation_prefix": "Fla. Fam. L. R. P.",
        "name": "Family Law Rules of Procedure",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Family-Law-Rules-of-Procedure"
    },
    "probate": {
        "citation_prefix": "Fla. Prob. R.",
        "name": "Probate Rules",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Probate-Rules"
    },
    "appellate": {
        "citation_prefix": "Fla. R. App. P.",
        "name": "Appellate Procedure",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Rules/Florida-Rules-of-Appellate-Procedure"
    }
}


def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = False) -> str:
    """Extract plain text from PDF. Use OCR if use_ocr=True or PDF has no text."""
    if use_ocr:
        # Use OCR for image-only PDFs
        print("  Using OCR (image-only PDF)...")
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        ocr = OCRProcessor()
        result = ocr.extract_from_pdf_images(pdf_bytes, lang="eng")
        return result["raw_text"]

    # Standard text extraction
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()

    # Check if we got any text
    if not text.strip() or len(text.strip()) < 100:
        print("  No extractable text found, falling back to OCR...")
        return extract_text_from_pdf(pdf_path, use_ocr=True)

    # Strip NULL bytes and control characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    return text


def parse_rules_from_text(text: str, rule_set: str) -> List[Dict]:
    """
    Parse individual rules from PDF text.

    Format example:
        RULE 2.110.
        SCOPE AND PURPOSE
        (a) ...
    """
    rules = []
    config = RULE_SETS[rule_set]

    # Find all RULE X.YYY pattern positions
    # Pattern: RULE followed by number, possibly with subsection like (a)
    # Handles: "RULE 2.110", "RULE 12.000.", "RULE 1.140(a)"
    rule_header_pattern = re.compile(r'RULE\s+(\d+\.\d+)([a-z]?)\.?\s*$', re.MULTILINE)

    # Find all matches
    matches = list(rule_header_pattern.finditer(text))

    for i, match in enumerate(matches):
        rule_number = match.group(1).strip()
        subsection = match.group(2).strip() or None

        # Determine where this rule's content ends (next rule or end of text)
        start_pos = match.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        rule_text = text[start_pos:end_pos].strip()

        # Extract title (first line after rule number, usually all caps)
        lines = rule_text.split('\n')
        title = ""
        for line in lines[1:10]:  # Check first few lines after header
            clean_line = line.strip()
            if clean_line and clean_line.isupper() and len(clean_line) > 3:
                # Found the title
                title = clean_line
                break
            elif clean_line and not clean_line.startswith('('):
                # Non-title content found, stop looking
                break

        # Create citation
        if subsection:
            citation = f"{config['citation_prefix']} {rule_number}({subsection})"
        else:
            citation = f"{config['citation_prefix']} {rule_number}"

        rules.append({
            "citation": citation,
            "rule_set": rule_set,
            "rule_number": rule_number,
            "subsection": subsection,
            "title": title,
            "text": rule_text,
            "effective_date": None,
            "source_url": config["url"],
            "jurisdiction": "FL"
        })

    return rules


def insert_rules_batch(rules: List[Dict], batch_size: int = 50) -> int:
    """Insert rules into Supabase in batches."""
    # Deduplicate by citation before inserting
    unique_rules = {}
    for rule in rules:
        citation = rule["citation"]
        if citation not in unique_rules:
            unique_rules[citation] = rule
        else:
            print(f"  ⚠ Duplicate citation skipped: {citation}")

    deduped_rules = list(unique_rules.values())
    print(f"  Deduplicated: {len(rules)} → {len(deduped_rules)} rules")

    inserted = 0
    failed = []

    for i in range(0, len(deduped_rules), batch_size):
        batch = deduped_rules[i:i + batch_size]
        try:
            # Upsert on citation
            response = supabase.table("court_rules").upsert(
                batch,
                on_conflict="citation"
            ).execute()
            inserted += len(batch)
            print(f"  ✓ Inserted batch {i//batch_size + 1}: {len(batch)} rules")
        except Exception as e:
            print(f"  ✗ Batch {i//batch_size + 1} failed: {e}")
            failed.extend([(r["citation"], str(e)) for r in batch])

    return inserted, failed


def main():
    """Main ingest function."""
    rules_dir = Path(__file__).parent.parent / "backend" / "src" / "data" / "rules"

    if not rules_dir.exists():
        print(f"Error: Rules directory not found: {rules_dir}")
        return

    all_rules = []

    print("Extracting rules from PDFs...")
    print("-" * 50)

    for rule_set, config in RULE_SETS.items():
        pdf_path = rules_dir / f"{rule_set}.pdf"

        if not pdf_path.exists():
            print(f"⚠ Skipping {rule_set}: PDF not found at {pdf_path}")
            continue

        print(f"📄 Processing {config['name']}...")

        try:
            text = extract_text_from_pdf(pdf_path)
            rules = parse_rules_from_text(text, rule_set)
            all_rules.extend(rules)
            print(f"  Extracted {len(rules)} rules")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("-" * 50)
    print(f"Total rules extracted: {len(all_rules)}")

    if not all_rules:
        print("No rules to insert. Exiting.")
        return

    print("\nInserting into Supabase...")
    print("-" * 50)

    inserted, failed = insert_rules_batch(all_rules)

    print("-" * 50)
    print(f"✓ Inserted: {inserted} rules")

    if failed:
        print(f"\n✗ Failed insertions: {len(failed)}")
        for citation, error in failed[:5]:
            print(f"  - {citation}: {error}")
        if len(failed) > 5:
            print(f"  ... and {len(failed) - 5} more")


if __name__ == "__main__":
    main()
