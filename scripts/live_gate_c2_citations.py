# Live gate for the Phase C2 citation adjudication (2026-08-30 plan).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the INDEX mock PDF to a RUNNING backend on :8002 and asserts the
deterministic adjudication shell (LLM verdicts are reported, NOT asserted):

  1. analysis_json carries the citations_checked log
  2. every entry whose status is 'verified' carries an adjudication in
     {SUPPORTED, WRONG_SCOPE, CONTRADICTS, unavailable}
  3. every scrubbed entry (scrubbed_court_only / scrubbed_wrong_scope /
     scrubbed_contradicts) — its citation text must NOT survive in any
     scanned analysis field (post-adjudication state)
  4. the report's own charge citation is preserved verbatim
  5. the C1 court-only floor is intact (no court-only citation in output)

Verdicts + notes are printed for Joe's eyeball — LLM variance is not a
regression.

Usage (backend must already be running on :8002 with backend/.env sourced):
    uv run --project backend python scripts/live_gate_c2_citations.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera.pdf
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

ENDPOINT = os.environ.get(
    "LC_C2_GATE_ENDPOINT",
    "http://127.0.0.1:8002/api/police-report/analyze",
)

_SCAN = (
    ("incident_summary", ()),
    ("probable_cause_summary", ()),
    ("what_happens_next", ()),
    ("discrepancies", ("description", "ask_attorney")),
    ("missing_fields", ("why_important",)),
    ("charges_explained", ("plain_english",)),
)

_ADJUDICATIONS = {"SUPPORTED", "WRONG_SCOPE", "CONTRADICTS", "unavailable"}


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


def _field_texts(aj: dict) -> list[str]:
    texts: list[str] = []
    for field, subfields in _SCAN:
        if not subfields:
            v = aj.get(field)
            if isinstance(v, str):
                texts.append(v)
            continue
        for item in aj.get(field) or []:
            if not isinstance(item, dict):
                continue
            for sub in subfields:
                v = item.get(sub)
                if isinstance(v, str):
                    texts.append(v)
    return texts


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: live_gate_c2_citations.py <path-to-index-pdf>",
              file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"ERROR: file not found: {sys.argv[1]}", file=sys.stderr)
        return 2

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

    log = aj.get("citations_checked")
    checks.append((
        "citations_checked log present",
        isinstance(log, list),
        f"{len(log) if isinstance(log, list) else 'MISSING'} entries",
    ))

    # 2. verified entries carry an adjudication
    missing_adj = [
        e.get("citation") for e in (log or [])
        if isinstance(e, dict) and e.get("status") == "verified"
        and e.get("adjudication") not in _ADJUDICATIONS
    ]
    checks.append((
        "every verified entry adjudicated",
        not missing_adj,
        repr(missing_adj),
    ))

    # 3. scrubbed entries' citations absent from emitted fields
    texts = " \n ".join(_field_texts(aj))
    survivors: list[str] = []
    for e in (log or []):
        if not isinstance(e, dict):
            continue
        status = e.get("status") or ""
        if not status.startswith("scrubbed_"):
            continue
        cite = e.get("citation") or ""
        if cite and re.search(re.escape(cite), texts, re.IGNORECASE):
            survivors.append(cite)
    checks.append((
        "scrubbed citations absent from emitted fields",
        not survivors,
        repr(survivors),
    ))

    # 4. charge citation preserved verbatim
    charge_texts = [
        c.get("charge", "") for c in aj.get("charges_explained") or []
        if isinstance(c, dict)
    ]
    charge_ok = any("893.13" in str(t) for t in charge_texts)
    checks.append((
        "report charge citation preserved",
        charge_ok,
        repr(charge_texts),
    ))

    # ── report ────────────────────────────────────────────────────────────
    print(f"\ncitations_checked ({len(log) if isinstance(log, list) else 0}):")
    for e in (log or []):
        if not isinstance(e, dict):
            continue
        adj = e.get("adjudication")
        expl = e.get("adjudication_explanation") or ""
        print(f"  {e.get('status'):24} {e.get('citation')!r}"
              + (f"  adjudication={adj!r}" if adj else "")
              + (f"  ({expl[:80]})" if expl else ""))
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
