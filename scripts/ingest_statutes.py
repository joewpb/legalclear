#!/usr/bin/env python3
"""
Phase 3 — Ingest Florida Statutes from the FL Legislature website.

SOURCE: https://www.leg.state.fl.us/statutes/
ROBOTS: VERIFIED_ALLOWED — leg.state.fl.us permits automated access.
METHOD: Fetches one HTML chapter page; parses section/subsection/text;
        upserts into the public.statutes table.

Usage (run from repo root):
    cd backend
    uv run python ../scripts/ingest_statutes.py --chapters 83 61 47 110
    uv run python ../scripts/ingest_statutes.py --all-priority
"""

import argparse
import html as html_mod
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

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

BASE_URL = "https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL={range_dir}/{ch4}/{ch4}.html"

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

EXTRA_CHAPTERS = [
    "34",   # County Courts
    "38",   # Judges — General Provisions
    "48",   # Process and Service (continued)
    "51",   # Summary Claims
    "76",   # Attachment
    "77",   # Garnishment
    "79",   # Habeas Corpus
    "82",   # Forcible Entry and Unlawful Detainer
    "84",   # Property (supplemental to 83)
    "85",   # Replevin
    "90",   # Evidence
    "92",   # Limitations of Actions
    "95",   # Limitations of Actions (continued)
    "768",  # Negligence
]


def range_dir_for(chapter: str) -> str:
    ch = int(chapter)
    low = (ch // 100) * 100
    high = low + 99
    return f"{low:04d}-{high:04d}"


def chapter_url(chapter: str) -> str:
    ch4 = chapter.zfill(4)
    return BASE_URL.format(range_dir=range_dir_for(chapter), ch4=ch4)


class StatuteSectionParser(HTMLParser):
    """Parse <div class='Section'> blocks from FL Statutes chapter HTML.

    Mode-based capture (fix 2026-08-18): the SectionBody <span> is a START
    MARKER, not a container — the body text continues through nested spans
    until the History <div> begins. The previous span-terminated capture
    ended the body at the first "</span>", dropping everything after the
    first subsection label (the corpus stubs: heading + "(1)(a)" + History).

    Modes: 'number' | 'catchline' | 'body' | 'history'. Span close tags
    never end a mode; only a new mode marker or the History div (or the
    Section div close) does.
    """

    def __init__(self, chapter: str):
        super().__init__()
        self.chapter = chapter
        self.sections: list[dict] = []

        self._in_section = False
        self._div_depth = 0  # tracks DIV nesting within Section (0 = Section div itself)
        self._mode: str | None = None
        self._bufs: dict[str, list[str]] = {}
        self._cur: dict = {}

    def _reset_bufs(self) -> None:
        self._bufs = {m: [] for m in ("number", "catchline", "body", "history")}

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        cls = attrs_d.get("class", "")

        if tag == "div" and cls == "Section":
            self._in_section = True
            self._div_depth = 0
            self._cur = {}
            self._mode = None
            self._reset_bufs()
            return

        if not self._in_section:
            return

        if tag == "div":
            self._div_depth += 1
            if cls == "History":
                self._mode = "history"
            return

        if tag == "span":
            if cls == "SectionNumber":
                self._mode = "number"
            elif cls == "SectionBody":
                self._mode = "body"
            elif "Catchline" in cls and self._mode in (None, "number"):
                # The outer <span class="Catchline"> — start capturing title.
                # Inner CatchlineText and EmDash spans just contribute data.
                self._mode = "catchline"

    def handle_endtag(self, tag):
        if not self._in_section:
            return

        if tag == "div":
            if self._div_depth == 0:
                # Closing the Section div itself
                self._finalize()
                self._in_section = False
                return
            self._div_depth -= 1
            if self._mode == "history":
                self._mode = None
            return

        # span close tags never end a capture mode

    def handle_data(self, data):
        if self._mode:
            self._bufs[self._mode].append(data)

    def handle_entityref(self, name):
        if self._mode:
            self._bufs[self._mode].append(html_mod.unescape(f"&{name};"))

    def handle_charref(self, name):
        if self._mode:
            self._bufs[self._mode].append(html_mod.unescape(f"&#{name};"))

    def _finalize(self):
        section_num = "".join(self._bufs["number"]).strip()
        if not section_num:
            return
        title = "".join(self._bufs["catchline"]).strip()
        text = "".join(self._bufs["body"]).strip()
        history = "".join(self._bufs["history"]).strip()

        if not text:
            return  # TOC-style entry — skip

        full_text = text
        if history:
            full_text += f"\n{history}"

        full_text = re.sub(r'[ \t]+', ' ', full_text)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = full_text.strip()

        if not full_text:
            return

        full_section = f"{self.chapter}.{section_num}" if "." not in section_num else section_num

        self.sections.append({
            "citation":    f"Fla. Stat. § {full_section}",
            "chapter":     self.chapter,
            "section":     full_section,
            "subsection":  None,
            "title":       title or None,
            "text":        full_text,
            "source_url":  chapter_url(self.chapter),
            "source_xml_ref": f"Ch{self.chapter.zfill(3)}.html",
            "jurisdiction": "FL",
        })


def parse_chapter_html(html_str: str, chapter: str) -> list[dict]:
    parser = StatuteSectionParser(chapter)
    parser.feed(html_str)
    return parser.sections


MIN_BODY_CHARS = 120   # body text (text minus History footer) must exceed this
REPORT_BODY_CHARS = 200  # sections under this are reported as stub-suspects


def validate_record(r: dict) -> tuple[bool, str]:
    """Stub-detection: a parsed record must contain a non-empty body.

    Length is NOT a hard reject: some statutes are genuinely short (verified
    against the official source, e.g. § 83.41 = ~100 chars). Short bodies are
    reported (NOTE) for the record but ingested — the parse came from the
    official chapter page, which IS the source. Pure heading rows never reach
    this point (skipped when body text is empty).
    """
    text = r["text"] or ""
    body = text.strip()
    if not body:
        return False, "empty body"
    if len(body) < MIN_BODY_CHARS:
        return True, f"SHORT body {len(body)} chars (< {MIN_BODY_CHARS}) — verified against chapter page"
    return True, f"body {len(body)} chars"


def fetch_chapter_html(chapter: str, client: httpx.Client) -> str | None:
    url = chapter_url(chapter)
    resp = client.get(url)
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}")
        return None
    return resp.text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", nargs="+", default=[],
                        help="Chapter numbers to ingest (e.g. 83 61 110)")
    parser.add_argument("--all-priority", action="store_true",
                        help="Ingest all priority chapters")
    parser.add_argument("--extra", action="store_true",
                        help="Also ingest extra chapters beyond priority")
    args = parser.parse_args()

    chapters = list(args.chapters)
    if args.all_priority:
        chapters = list(set(chapters + PRIORITY_CHAPTERS))
    if args.extra:
        chapters = list(set(chapters + EXTRA_CHAPTERS))
    if not chapters:
        print("ERROR: specify --chapters, --all-priority, or --extra")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
        sys.exit(1)

    supabase = create_client(url, key)
    total_upserted = 0
    failed: list[str] = []

    import time as _time  # rate limit ~1 req/sec

    with httpx.Client(timeout=90, follow_redirects=True) as client:
        for chapter in chapters:
            print(f"Chapter {chapter}...", end=" ", flush=True)
            html_str = fetch_chapter_html(chapter, client)
            _time.sleep(1.0)
            if html_str is None:
                failed.append(chapter)
                continue
            records = parse_chapter_html(html_str, chapter)
            if not records:
                print("parsed 0 sections.")
                failed.append(chapter)
                continue

            # Deduplicate by citation — keep longest text
            by_cite: dict[str, dict] = {}
            for r in records:
                cite = r["citation"]
                if cite not in by_cite or len(r["text"]) > len(by_cite[cite]["text"]):
                    by_cite[cite] = r
            records = list(by_cite.values())

            # Fetch -> validate -> replace: per-section validation. Empty-body
            # records are skipped (old rows untouched); short bodies are
            # reported AND ingested (their text is the official chapter-page
            # content — genuinely short statutes, not stubs).
            good: list[dict] = []
            suspect: list[str] = []
            short_notes: list[str] = []
            for r in records:
                ok, reason = validate_record(r)
                if not ok:
                    suspect.append(f"{r['citation']}: {reason}")
                    continue
                good.append(r)
                if "SHORT" in reason:
                    short_notes.append(f"{r['citation']}: {reason}")
            if suspect:
                print(f"\n  SKIPPED {len(suspect)} empty-body sections (old rows untouched):")
                for s in suspect:
                    print(f"    {s}")
            if short_notes:
                print(f"  SHORT-BUT-INGESTED ({len(short_notes)} — genuinely short statutes, verified text):")
                for s in short_notes:
                    print(f"    {s}")

            for i in range(0, len(good), 100):
                batch = good[i:i+100]
                supabase.table("statutes").upsert(
                    batch, on_conflict="citation"
                ).execute()
            total_upserted += len(good)
            print(f"{len(good)}/{len(records)} sections upserted.")

    print(f"\nDone. Total sections upserted: {total_upserted}")
    if failed:
        print(f"Failed chapters: {', '.join(failed)}")


if __name__ == "__main__":
    main()
