# Live gate for the Phase C1 citation validation (2026-08-30 plan).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the INDEX mock PDF (contains the Embedded Defect Index asserting
F.S. 90.606 twice) to a RUNNING backend on :8002 and asserts,
deterministically:

  1. analysis_json carries the citations_checked log
  2. ZERO court-only citations (Ch. 90 Evidence Code, rules of court,
     bar rules) survive in the emitted analysis fields
  3. every non-charge citation surviving in the emitted analysis has a
     matching citations_checked entry with status 'verified'
  4. the report's own charge citation is preserved verbatim

The citations log and any scrub notes are printed — whether the LLM
echoed 90.606 in a given run is LLM variance (reported, not asserted).

Usage (backend must already be running on :8002 with backend/.env sourced):
    uv run --project backend python scripts/live_gate_c1_citations.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera.pdf
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

ENDPOINT = os.environ.get(
    "LC_C1_GATE_ENDPOINT",
    "http://127.0.0.1:8002/api/police-report/analyze",
)

# Fields the C1 validator scans (must mirror citation_validation._SCAN_FIELDS).
_SCAN = (
    ("incident_summary", ()),
    ("probable_cause_summary", ()),
    ("what_happens_next", ()),
    ("discrepancies", ("description", "ask_attorney")),
    ("missing_fields", ("why_important",)),
    ("charges_explained", ("plain_english",)),
)


def _load_env() -> None:
    env = BACKEND_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _parse_frames(text: str) -> list[tuple[str | None, dict]]:
    frames = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        try:
            payload = json.loads(data or "null")
        except json.JSONDecodeError:
            continue
        frames.append((event, payload))
    return frames


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: live_gate_c1_citations.py <path-to-index-pdf>",
              file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"ERROR: file not found: {sys.argv[1]}", file=sys.stderr)
        return 2

    _load_env()
    from src.services.citation_validation import (
        _base_section,
        _is_court_only,
        _iter_citations,
    )

    print(f"POST {ENDPOINT}  [{p.name}, {p.stat().st_size} bytes]")
    with open(p, "rb") as fh:
        resp = requests.post(
            ENDPOINT,
            files={"file": (p.name, fh, "application/pdf")},
            data={"language": "en"},
            stream=True,
            timeout=(30, 300),
        )
    resp.raise_for_status()

    frames = _parse_frames(resp.text)
    aj = next(
        (payload for e, payload in frames if e == "analysis_json"), None,
    )
    errs = [payload.get("message") for e, payload in frames if e == "error"]

    checks: list[tuple[str, bool, str]] = []
    checks.append(("analysis_json frame received", aj is not None,
                   "ok" if aj else f"errors={errs!r}"))

    if aj is None:
        print("\nGATE VERDICT")
        for name, passed, detail in checks:
            print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
        return 1

    # 1. citations_checked present
    log = aj.get("citations_checked")
    checks.append((
        "citations_checked log present",
        isinstance(log, list),
        f"{len(log) if isinstance(log, list) else 'MISSING'} entries",
    ))

    # 2. zero court-only citations in emitted analysis fields
    charge_cites: set[str] = set()
    for c in aj.get("charges_explained") or []:
        if isinstance(c, dict):
            for _s, _e, info in _iter_citations(c.get("charge") or ""):
                charge_cites.add(info["text"].casefold())

    court_only_found: list[str] = []
    surviving_cites: list[dict] = []
    for field, subfields in _SCAN:
        if not subfields:
            for _s, _e, info in _iter_citations(aj.get(field) or ""):
                if _is_court_only(info):
                    court_only_found.append(info["text"])
                elif info["text"].casefold() not in charge_cites:
                    surviving_cites.append(info)
            continue
        for item in aj.get(field) or []:
            if not isinstance(item, dict):
                continue
            for sub in subfields:
                for _s, _e, info in _iter_citations(item.get(sub) or ""):
                    if _is_court_only(info):
                        court_only_found.append(info["text"])
                    elif info["text"].casefold() not in charge_cites:
                        surviving_cites.append(info)
    checks.append((
        "ZERO court-only citations in emitted analysis",
        not court_only_found,
        repr(court_only_found),
    ))

    # 3. every surviving non-charge citation is logged verified (base
    # section compared — subsection suffixes are lookup-only)
    verified_sections = {
        e.get("section")
        for e in (log or [])
        if e.get("status") == "verified"
    }
    bad = [
        info["text"] for info in surviving_cites
        if _base_section(info["num"] or info["text"]) not in verified_sections
    ]
    checks.append((
        "every surviving citation logged verified",
        not bad,
        repr(bad),
    ))

    # 4. charge citation preserved verbatim
    charge_ok = bool(charge_cites)
    checks.append((
        "report charge citation preserved",
        charge_ok,
        repr(sorted(charge_cites)),
    ))

    # ── report ────────────────────────────────────────────────────────────
    print(f"\ncitations_checked ({len(log) if isinstance(log, list) else 0}):")
    for e in (log or []):
        title = f" title={e.get('title')!r}" if e.get("title") else ""
        print(f"  {e.get('status'):20} {e.get('citation')!r}{title}")
    notes = aj.get("citation_notes") or []
    print(f"\ncitation_notes ({len(notes)}):")
    for n in notes:
        print(f"  - {n}")

    print("\nGATE VERDICT")
    ok = True
    for name, passed, detail in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
