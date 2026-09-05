# Live gate for the Phase A SSE protocol fix (2026-08/09).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the NOINDEX mock PDF to a RUNNING backend on :8002 and asserts the
RAW stream shape: every frame carries an `event:` name from the allowed set,
every data: payload is complete JSON, exactly one analysis_json /
risk_analysis / relevant_opinions / case_context frame, and ZERO per-token
fragments (frame count small and bounded).

Usage (backend must already be running on :8002 with backend/.env sourced):
    uv run --project backend python scripts/live_gate_a_sse.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera_NOINDEX.pdf
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

ENDPOINT = os.environ.get(
    "LC_A_GATE_ENDPOINT",
    "http://127.0.0.1:8002/api/police-report/analyze",
)
ALLOWED_EVENTS = {
    "progress",
    "analysis_json",
    "risk_analysis",
    "relevant_opinions",
    "case_context",
    "error",
}


def parse_stream(text: str) -> list[tuple[str | None, str | None]]:
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
        frames.append((event, data))
    return frames


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: live_gate_a_sse.py <path-to-noindex-pdf>",
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

    frames = parse_stream(resp.text)

    print(f"\nraw stream: {len(frames)} frame(s)")
    for e, d in frames:
        print(f"  event={e}  data={(d or '')[:110]!r}")
    print()

    checks: list[tuple[str, bool, str]] = []

    # 1. Every frame has an event name from the allowed set.
    bad = [(e, (d or "")[:60]) for e, d in frames if e not in ALLOWED_EVENTS]
    checks.append((
        "every frame named + allowed type",
        not bad,
        f"{len(bad)} bad frames: {bad!r}",
    ))

    # 2. Every data payload parses as complete JSON.
    parsed: list[tuple[str, dict]] = []
    unparseable: list[tuple[str | None, str]] = []
    for e, d in frames:
        try:
            parsed.append((e, json.loads(d or "null")))
        except json.JSONDecodeError:
            unparseable.append((e, (d or "")[:60]))
    checks.append((
        "ZERO unparseable data lines",
        not unparseable,
        f"{len(unparseable)}: {unparseable!r}",
    ))

    # 3. Exactly one of each typed event.
    by_event: dict[str, list[dict]] = {}
    for e, obj in parsed:
        by_event.setdefault(e, []).append(obj)
    for want in ("analysis_json", "risk_analysis",
                 "relevant_opinions", "case_context"):
        n = len(by_event.get(want, []))
        checks.append((f"exactly one {want}", n == 1, f"{n} frame(s)"))

    # 4. No per-token fragments: a fragment stream is ~100 frames; the
    # protocol adds typed heartbeats on long analyses (char/timer cadence),
    # so the bound allows a handful of progress frames beyond the six
    # core events.
    checks.append((
        "no per-token fragments (frames <= 12)",
        len(frames) <= 12,
        f"{len(frames)} frames",
    ))

    # 5. analysis_json is complete (has the analysis fields, not a shard).
    aj = by_event.get("analysis_json", [{}])[0]
    checks.append((
        "analysis_json complete (incident_summary present)",
        bool(aj.get("incident_summary")),
        f"keys={sorted(aj.keys())!r}",
    ))

    # 6. Happy path carries no error frame.
    errs = [o.get("message") for o in by_event.get("error", [])]
    checks.append(("no error frames", not errs, repr(errs)))

    # 7. Progress heartbeats present (keeps proxies from buffering).
    stages = [o.get("stage") for e, o in parsed if e == "progress"]
    checks.append((
        "progress heartbeats present",
        "analyzing" in stages,
        f"stages={stages!r}",
    ))

    print("GATE VERDICT")
    ok = True
    for name, passed, detail in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
