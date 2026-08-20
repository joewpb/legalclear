#!/usr/bin/env python3
"""STATUS.md prose writer — appends a session entry between the PROSE markers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "STATUS.md"

text = STATUS.read_text()
entry = sys.stdin.read().strip()
if not entry:
    raise SystemExit("no entry on stdin")

marker = "<!-- PROSE:END -->"
if marker not in text:
    raise SystemExit(f"{marker} not found in STATUS.md")
text = text.replace(marker, entry + "\n\n" + marker, 1)
STATUS.write_text(text)
print("prose written")
