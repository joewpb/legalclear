"""
Phase 8 — Legal information disclaimers.

Thin delegator to `apply_disclaimer` in src/core/upl.py, which is the
canonical, versioned disclaimer source (Decision 3, DECISIONS.md). This
module exists only to preserve the `get_disclaimer(lang, level)` call
signature for existing callers.
"""

from src.core.upl import apply_disclaimer


def get_disclaimer(lang: str, level: str = "standard") -> str:
    return apply_disclaimer({}, lang=lang, level=level)["disclaimer"]
