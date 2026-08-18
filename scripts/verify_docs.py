#!/usr/bin/env python3
"""Mechanically prove SPEC_LEDGER.md's claims against the tree.

Checks, in order:
  1. Every backticked code path and test path in the SPEC_LEDGER capability
     ledger table exists as a file in the repo.
  2. Grep-level assertions: the ledger carries the verification date and SHA;
     files deleted in Phase G are absent; routes.py contains no push-token or
     top-level /eligibility surface; the triage router is still marked AMBIGUOUS.

File-existence and grep assertions only — no network, no pytest.
Prints PASS/FAIL per entry; exits non-zero if anything fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "SPEC_LEDGER.md"

# Backticked tokens in the ledger's path columns that look like file paths.
PATH_RE = re.compile(r"`([^`]+/[^`]+\.(?:py|ts|tsx|js|jsx|md|sql|yml|yaml|json))`")

MUST_BE_ABSENT = [
    "backend/src/api/routers/analysis.py",
    "frontend/src/pages/AnalysisDashboard.jsx",
    "frontend/src/pages/LandingPage.jsx",
    "frontend/src/pages/ExpungementPage.jsx",
    "frontend/src/pages/PhaseStub.tsx",
    "frontend/src/components/layout/Navbar.jsx",
]

GREP_ASSERTIONS = [
    # (file, pattern, must_match, label)
    ("SPEC_LEDGER.md", r"f145dd8", True, "ledger records verified SHA f145dd8"),
    ("SPEC_LEDGER.md", r"2026-08-17", True, "ledger records verified date 2026-08-17"),
    ("SPEC_LEDGER.md", r"AMBIGUOUS", True, "ledger marks the triage router AMBIGUOUS"),
    ("backend/src/api/routes.py", r"push_token", False, "routes.py has no push-token surface"),
    ("backend/src/api/routes.py", r"@app\.post\(\"/eligibility\"", False, "routes.py has no top-level /eligibility"),
    ("backend/src/api/routes.py", r"analysis_router", False, "routes.py does not register the deleted analysis router"),
    ("docs/ADRS.md", r"deterministic database retrieval, not LLM", True, "ADR-1 (case law deterministic) present verbatim"),
]


def ledger_table_paths() -> list[tuple[str, str]]:
    """Yield (capability, path) for the code-path and test-path columns of the
    capability ledger table."""
    text = LEDGER.read_text(encoding="utf-8")
    try:
        section = text.split("## Capability ledger", 1)[1].split("\n---", 1)[0]
    except IndexError:
        sys.exit("FAIL  SPEC_LEDGER.md has no '## Capability ledger' section")
    out: list[tuple[str, str]] = []
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[0] in ("Capability",):
            continue
        capability = cells[0].strip("*` ")
        for cell in (cells[3], cells[4]):  # code path, test path
            for path in PATH_RE.findall(cell):
                out.append((capability, path))
    return out


def main() -> int:
    failures = 0
    checks = 0

    paths = ledger_table_paths()
    if not paths:
        print("FAIL  no paths parsed from the capability ledger table")
        return 1

    for capability, path in paths:
        checks += 1
        if (REPO / path).is_file():
            print(f"PASS  [{capability}] {path}")
        else:
            print(f"FAIL  [{capability}] {path} — file missing from tree")
            failures += 1

    for path in MUST_BE_ABSENT:
        checks += 1
        if (REPO / path).exists():
            print(f"FAIL  [absence] {path} exists but Phase G deleted it")
            failures += 1
        else:
            print(f"PASS  [absence] {path} absent as claimed")

    for rel, pattern, must_match, label in GREP_ASSERTIONS:
        checks += 1
        target = REPO / rel
        if not target.is_file():
            print(f"FAIL  [grep] {rel} missing — cannot assert: {label}")
            failures += 1
            continue
        found = re.search(pattern, target.read_text(encoding="utf-8")) is not None
        if found == must_match:
            print(f"PASS  [grep] {label}")
        else:
            print(f"FAIL  [grep] {label} (pattern {pattern!r} in {rel}: found={found})")
            failures += 1

    print(f"\nSUMMARY: {checks - failures}/{checks} checks passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
