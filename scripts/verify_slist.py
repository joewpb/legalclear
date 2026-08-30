#!/usr/bin/env python3
"""verify_slist.py — FOLLOW_UPS list-hygiene gate (Decision 21).

The class this kills: entries written at diagnosis time and never closed when
the fix landed (S2-7, the rate-limit entry, the closure-rows entry — three
instances, each of which burned a session's planning). The open list is what
we plan from; stale blockers on it mislead the next dispatch.

Deterministic bookkeeping check, no LLM, no prose matching:

  1. Every FOLLOW_UPS.md heading must carry the grammar:
     ``## <ID> — <STATE> ...`` where STATE ∈ {OPEN, OPEN (deliberate),
     RESOLVED, RECORDED, DEFERRED}. Entries without an ID are invisible to
     this gate — a grammar violation is FATAL, not a warning.

  2. A commit whose subject declares ``fixes <ID>`` for an entry still marked
     OPEN is FATAL: the fix landed, the list was never back-annotated. Close
     the entry (RESOLVED + evidence) or mark it ``OPEN (deliberate)`` with a
     reason — the gate forces the decision, it does not make it.

  3. A ``fixes <ID>`` whose ID exists in NO entry is a WARNING (possible typo
     or an entry that should exist). Warnings do not fail CI.

Exit 1 on any flag. Green because nothing is wrong, not because violations are
expected — same policy as verify_educational.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STATES = ("OPEN", "RESOLVED", "RECORDED", "DEFERRED")
HEADING_RE = re.compile(
    r"^##\s+(?P<id>\S+)\s+—\s+"
    r"(?P<state>OPEN\b( \(deliberate\))?|RESOLVED|RECORDED|DEFERRED)",
    re.MULTILINE,
)
FIXES_RE = re.compile(r"\bfixes\s+([A-Za-z][A-Za-z0-9]*-[A-Za-z0-9-]+)", re.IGNORECASE)


@dataclass(frozen=True)
class Entry:
    id: str
    state: str
    deliberate: bool
    heading: str
    lineno: int


def parse_entries(text: str) -> dict[str, Entry]:
    """Map entry ID -> Entry from all well-formed headings."""
    entries: dict[str, Entry] = {}
    for m in HEADING_RE.finditer(text):
        eid = m.group("id")
        state = m.group("state")
        deliberate = "deliberate" in state
        base = "OPEN" if state.startswith("OPEN") else state
        entries[eid] = Entry(
            id=eid,
            state=base,
            deliberate=deliberate,
            heading=m.group(0).strip(),
            lineno=text[: m.start()].count("\n") + 1,
        )
    return entries


def bad_headings(text: str) -> list[tuple[int, str]]:
    """Headings that do not match the grammar, as (lineno, heading)."""
    out = []
    for m in re.finditer(r"^##\s+(.+)$", text, re.MULTILINE):
        heading = m.group(0).strip()
        if not HEADING_RE.match(heading):
            out.append((text[: m.start()].count("\n") + 1, heading))
    return out


def extract_fixes(subject: str) -> set[str]:
    return {m.group(1) for m in FIXES_RE.finditer(subject)}


def git_log_subjects(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def scan(root: Path) -> tuple[list[str], list[str]]:
    """Return (flags, warnings) for the repo at ``root``."""
    flags: list[str] = []
    warnings: list[str] = []
    f = root / "FOLLOW_UPS.md"
    if not f.exists():
        return [f"FOLLOW_UPS.md missing at {f}"], []

    text = f.read_text()
    entries = parse_entries(text)
    for lineno, heading in bad_headings(text):
        flags.append(
            f"FOLLOW_UPS.md:{lineno}: heading does not match the "
            f"`## <ID> — <STATE>` grammar: {heading!r}"
        )

    for subject in git_log_subjects(root):
        for fid in extract_fixes(subject):
            if fid in entries:
                e = entries[fid]
                if e.state == "OPEN" and not e.deliberate:
                    flags.append(
                        f"entry {fid} is OPEN but a commit declares "
                        f"'fixes {fid}': {subject}"
                    )
            else:
                warnings.append(
                    f"commit declares 'fixes {fid}' but FOLLOW_UPS.md "
                    f"has no entry {fid}: {subject}"
                )
    return flags, warnings


def main() -> int:
    flags, warnings = scan(ROOT)
    for w in warnings:
        print(f"WARNING  {w}")
    for fl in flags:
        print(f"FLAG     {fl}")
    print(
        f"\nverify_slist: {len(flags)} flag(s), {len(warnings)} warning(s)."
    )
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
