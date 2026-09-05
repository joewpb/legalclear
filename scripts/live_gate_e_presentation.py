# Live gate for the Phase E presentation flag (2026-08-30 plan).
# Diagnostic-only. Mutates nothing. Run by hand, NOT in CI.
"""POSTs the NOINDEX mock PDF to a RUNNING backend on :8002 and asserts the
deterministic miranda_validity_concern wiring:

  1. analysis_json carries miranda_validity_concern (a bool, never absent)
  2. local computation from the SAME analysis JSON equals the server's
     value (the flag is deterministic given the JSON — LLM variance in the
     findings cannot fail this gate)

The flag value + the findings that produced it are printed for Joe's
eyeball (whether the warning badge renders for a given run is LLM output,
not a regression).

Usage (backend must already be running on :8002 with backend/.env sourced):
    uv run --project backend python scripts/live_gate_e_presentation.py \\
        /home/hermes/incoming/MOCK_Police_Report_Herrera_NOINDEX.pdf
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
    "LC_E_GATE_ENDPOINT",
    "http://127.0.0.1:8002/api/police-report/analyze",
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
        print("usage: live_gate_e_presentation.py <path-to-noindex-pdf>",
              file=sys.stderr)
        return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"ERROR: file not found: {sys.argv[1]}", file=sys.stderr)
        return 2

    _load_env()
    from src.agents.police_report_v2 import miranda_validity_concern  # noqa: E402

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

    flag = aj.get("miranda_validity_concern")
    checks.append((
        "miranda_validity_concern present and boolean",
        isinstance(flag, bool),
        repr(flag),
    ))

    local = miranda_validity_concern(aj)
    checks.append((
        "local compute == server value",
        local == flag,
        f"local={local!r} server={flag!r}",
    ))

    # ── report ────────────────────────────────────────────────────────────
    print(f"\nmiranda_noted = {aj.get('miranda_noted')!r}")
    print(f"miranda_validity_concern = {flag!r}")
    print("relevant findings:")
    for d in aj.get("discrepancies") or []:
        if not isinstance(d, dict):
            continue
        if d.get("defect_category") in ("miranda", "language_access"):
            print(f"  - [{d.get('severity')}] {d.get('defect_category')}: "
                  f"{(d.get('description') or '')[:90]}")
    print("\n(If the warning badge does not show on a given run, that is "
          "LLM variance in the findings — not a code regression.)")

    print("\nGATE VERDICT")
    ok = True
    for name, passed, detail in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
