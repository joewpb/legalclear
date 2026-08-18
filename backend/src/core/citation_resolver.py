"""Citation resolution guard (Dispatch J1).

Doctrine: before any citation reaches a user it must resolve to a row in the
owned ``statutes`` or ``court_rules`` tables. Unresolvable citations are
stripped — never displayed, never passed through. Coverage gaps degrade to
silence, not fabrication. Same doctrine as ``core/url_filter.py`` —
deterministic code guarantees what the prompt cannot.

Normalization is formatting-only (whitespace, section-sign variants, casing
of known abbreviations). It never fuzzy-matches substance — a citation that
normalizes cleanly but isn't in the owned map is suppressed, not guessed at.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitationResolution:
    citation: str
    source_url: str
    section: str | None
    title: str | None


_WHITESPACE_RE = re.compile(r"\s+")
# "s.", "sec.", "section" (with optional trailing period, case-insensitive) -> "§"
_SECTION_WORD_RE = re.compile(r"\b(?:sec(?:tion)?|s)\.?\s*(?=\d)", re.IGNORECASE)
_KNOWN_PREFIXES = (
    "FLA. STAT.",
    "FLA. R. CIV. P.",
    "FLA. R. CRIM. P.",
    "FLA. SM. CL. R.",
    "FLA. R. APP. P.",
    "FLA. FAM. L. R. P.",
    "FLA. PROB. R.",
    "FLA. R. JUD. ADMIN.",
)


def normalize_citation(raw: str) -> str:
    """Collapse whitespace and unify formatting variants of a citation.

    Conservative by design: normalizes punctuation/casing only, never
    fuzzy-matches substance. "fla. stat.   s.34.01" and "§ 34.01" both
    normalize toward a consistent form, but no chapter/section value is
    ever altered.
    """
    text = raw.strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = _SECTION_WORD_RE.sub("§ ", text)
    # unify "§34.01" -> "§ 34.01" (ensure single space after the sign)
    text = re.sub(r"§\s*", "§ ", text)
    upper = text.upper()
    for prefix in _KNOWN_PREFIXES:
        if upper.startswith(prefix):
            rest = text[len(prefix):]
            text = prefix + rest
            upper = text.upper()
            break
    text = _WHITESPACE_RE.sub(" ", text).strip()
    # A bare "§ 34.01" with no rule-set/statute prefix at all defaults to
    # "Fla. Stat." — the overwhelmingly common bare form in FL legal text.
    # This is a documented formatting default, not a substance guess: it
    # never overrides an explicit prefix, and it never resolves a citation
    # to anything other than what its own text says.
    if re.match(r"^§\s*\d", text):
        text = "FLA. STAT. " + text
    return text


def resolve_citation(
    citation: str, owned: Mapping[str, CitationResolution]
) -> CitationResolution | None:
    """Exact match on normalized form against a preloaded owned-citation map."""
    return owned.get(normalize_citation(citation))


def resolve_citations(
    citations: Iterable[str], owned: Mapping[str, CitationResolution]
) -> list[CitationResolution]:
    """Return only the resolvable citations, in input order, deduped."""
    resolved: list[CitationResolution] = []
    seen: set[str] = set()
    for citation in citations:
        match = resolve_citation(citation, owned)
        if match is None:
            continue
        if match.citation in seen:
            continue
        seen.add(match.citation)
        resolved.append(match)
    return resolved


def load_owned_citations(db) -> dict[str, CitationResolution]:
    """Load the owned citation map from the ``statutes`` and ``court_rules`` tables.

    Follows the DatabaseManager pattern used elsewhere (e.g. law.py,
    opinion_retrieval.py). Degrades gracefully — a missing client or a
    failed query returns an empty map, which suppresses every citation
    rather than raising to the caller.
    """
    owned: dict[str, CitationResolution] = {}
    if db is None or getattr(db, "client", None) is None:
        return owned

    try:
        result = db.client.table("statutes").select(
            "citation,section,title,source_url"
        ).execute()
        for row in result.data or []:
            key = normalize_citation(row["citation"])
            owned[key] = CitationResolution(
                citation=row["citation"],
                source_url=row.get("source_url"),
                section=row.get("section"),
                title=row.get("title"),
            )
    except Exception as e:
        logger.error("load_owned_citations: statutes lookup failed: %s", e)

    try:
        result = db.client.table("court_rules").select(
            "citation,rule_number,title,source_url"
        ).execute()
        for row in result.data or []:
            key = normalize_citation(row["citation"])
            owned[key] = CitationResolution(
                citation=row["citation"],
                source_url=row.get("source_url"),
                section=row.get("rule_number"),
                title=row.get("title"),
            )
    except Exception as e:
        logger.error("load_owned_citations: court_rules lookup failed: %s", e)

    return owned
