#!/usr/bin/env python3
"""
Phase 3 — Ingest Florida Statutes from the FL Legislature bulk XML.

SOURCE: https://www.leg.state.fl.us/statutes/download/
ROBOTS: VERIFIED_ALLOWED — leg.state.fl.us permits bulk download access.
METHOD: Downloads one XML file per chapter; parses section/subsection/text;
        upserts into the public.statutes table.

Usage (run from repo root):
    cd backend
    uv run python ../scripts/ingest_statutes.py --chapters 83 61 47 110
    uv run python ../scripts/ingest_statutes.py --all-priority

Chapters are specified by number (e.g. 83 for Ch. 083 Landlord and Tenant).
The script zero-pads to 3 digits for the XML filename.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase package not found. Run: cd backend && uv sync")
    sys.exit(1)

BULK_XML_BASE = "https://www.leg.state.fl.us/statutes/download/statutes/2025"
SOURCE_BASE   = "https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=Ch"

PRIORITY_CHAPTERS = [
    "83",   # Landlord and Tenant
    "47",   # Process and Service
    "55",   # Judgments
    "56",   # Executions
    "57",   # Costs
    "61",   # Dissolution of Marriage
    "63",   # Adoption
    "68",   # Civil Actions by/against State
    "69",   # Actions
    "86",   # Declaratory Judgments
    "110",  # State Employment (holidays § 110.117)
]


def xml_filename(chapter: str) -> str:
    padded = chapter.zfill(3)
    return f"Title_?_Ch{padded}.xml"


def fetch_chapter_xml(chapter: str, client: httpx.Client) -> bytes | None:
    """Try to fetch the chapter XML; returns None if not found."""
    padded = chapter.zfill(3)
    # FL Legislature uses Title groupings; try common ones
    for title_num in range(1, 50):
        url = f"{BULK_XML_BASE}/Title_{title_num:02d}_Ch{padded}.xml"
        resp = client.head(url)
        if resp.status_code == 200:
            return client.get(url).content
    return None


def parse_chapter_xml(xml_bytes: bytes, chapter: str) -> list[dict]:
    """Parse FL Statutes XML into individual section records."""
    records = []
    try:
        root = ET.fromstring(xml_bytes)
        ns = {"s": root.tag.split("}")[0].lstrip("{")} if "}" in root.tag else {}

        def find_text(el, tag):
            found = el.find(f".//{tag}")
            if found is not None and found.text:
                return found.text.strip()
            return None

        for section_el in root.iter():
            if not section_el.tag.endswith(("Section", "Statute", "SECTION")):
                continue
            section_num = (find_text(section_el, "SectionNumber") or
                          find_text(section_el, "section_number") or "")
            if not section_num:
                continue
            title = (find_text(section_el, "Catchline") or
                    find_text(section_el, "catchline") or
                    find_text(section_el, "Title") or "")
            text = " ".join(
                (el.text or "").strip()
                for el in section_el.iter()
                if el.text and el.text.strip()
            )
            if not text:
                continue
            full_section = f"{chapter}.{section_num}" if "." not in section_num else section_num
            records.append({
                "citation":    f"Fla. Stat. § {full_section}",
                "chapter":     chapter,
                "section":     full_section,
                "subsection":  None,
                "title":       title or None,
                "text":        text,
                "source_url":  f"{SOURCE_BASE}{chapter.zfill(3)}.htm",
                "source_xml_ref": f"Ch{chapter.zfill(3)}.xml",
                "jurisdiction": "FL",
            })
    except Exception as e:
        print(f"  WARNING: XML parse failed for chapter {chapter}: {e}")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", nargs="+", default=[],
                        help="Chapter numbers to ingest (e.g. 83 61 110)")
    parser.add_argument("--all-priority", action="store_true",
                        help="Ingest all priority chapters")
    args = parser.parse_args()

    chapters = args.chapters
    if args.all_priority:
        chapters = list(set(chapters + PRIORITY_CHAPTERS))
    if not chapters:
        print("ERROR: specify --chapters or --all-priority")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        sys.exit(1)

    supabase = create_client(url, key)
    total_upserted = 0

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for chapter in chapters:
            print(f"Chapter {chapter}...", end=" ", flush=True)
            xml_bytes = fetch_chapter_xml(chapter, client)
            if xml_bytes is None:
                print("NOT FOUND — check the XML URL manually.")
                continue
            records = parse_chapter_xml(xml_bytes, chapter)
            if not records:
                print(f"parsed 0 sections (check XML structure).")
                continue
            # Upsert in batches of 100
            for i in range(0, len(records), 100):
                batch = records[i:i+100]
                supabase.table("statutes").upsert(
                    batch, on_conflict="citation"
                ).execute()
            total_upserted += len(records)
            print(f"{len(records)} sections upserted.")

    print(f"\nDone. Total sections upserted: {total_upserted}")


if __name__ == "__main__":
    main()
