"""Decision 7 (2026-08): DeepSeek retired from all production call sites.

Every DeepSeek call site (opinion_retrieval.py's attorney-question
generator, orin_opinions.py's metadata batch extractor, attorney_referral.py's
intake fallback) was repointed to Claude Haiku. This test grep-scans
`backend/src` for any remaining "deepseek" reference and fails unless the
line is `DEEPSEEK_API_KEY` plumbing (kept inert — see config.py) or a
comment explicitly documenting the retirement.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"

# Lines allowed to mention "deepseek": the inert env-var plumbing itself,
# and comments that explicitly document the Decision 7 retirement.
_ALLOWED_PATTERNS = (
    re.compile(r"DEEPSEEK_API_KEY\s*:\s*str\s*=\s*os\.getenv"),
    re.compile(r"Retired \(Decision 7", re.IGNORECASE),
)

_DEEPSEEK_RE = re.compile(r"deepseek", re.IGNORECASE)


def test_no_active_deepseek_call_sites():
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not _DEEPSEEK_RE.search(line):
                continue
            if any(p.search(line) for p in _ALLOWED_PATTERNS):
                continue
            offenders.append(f"{path.relative_to(SRC_ROOT.parent)}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Found unexpected DeepSeek reference(s) in production code "
        "(Decision 7 retired DeepSeek in favor of Claude Haiku):\n"
        + "\n".join(offenders)
    )


def test_no_deepseek_endpoint_urls_in_production():
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "api.deepseek.com" in text:
            offenders.append(str(path.relative_to(SRC_ROOT.parent)))
    assert not offenders, f"DeepSeek API endpoint still referenced in: {offenders}"
