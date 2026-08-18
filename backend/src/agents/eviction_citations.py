"""Eviction curated citation set (Dispatch J3 — ch. 83, section-level ONLY).

These are the ONLY ch. 83 citations the codebase cites anywhere (verified by
a repo-wide grep): the deadline engine's worked examples, the landlord
packet, and the ES/EN instruction text. Each entry was verified by the
orchestrator against prod (citation -> row lookup -> text present ->
source_url on leg.state.fl.us) before being pinned here. This is a strict
subset of the owned ``statutes`` rows loaded by
``core.citation_resolver.load_owned_citations`` — never a superset.

SECTION-LEVEL ONLY: the owned § 83.60 row's text is abridged and does NOT
contain subsection (2). The deterministic deadline engine
(``deadline/rules.py`` ``governing_rule``) cites "Fla. Stat. § 83.60(2)" for
the 5-business-day answer deadline — that subsection-level granularity is
code-declared, computed by deterministic logic, and test-locked in the
deadline engine's worked examples. It is never model-emitted, so it has no
place in this curated set. Do NOT add "Fla. Stat. § 83.60(2)" here.

``source_url`` follows the same chapter-page pattern used by
``scripts/ingest_statutes.py`` (``chapter_url()``): every section in ch. 83
shares one Display_Statute URL, since FL Statutes source pages are chapter-
level, not per-section.
"""

from __future__ import annotations

from src.core.citation_resolver import CitationResolution, normalize_citation

_CH_83_SOURCE_URL = (
    "https://www.leg.state.fl.us/statutes/index.cfm"
    "?App_mode=Display_Statute&URL=0000-0099/0083/0083.html"
)

_ENTRIES = (
    (
        "Fla. Stat. § 83.49",
        "Deposit money or advance rent; duty of landlord and tenant",
    ),
    ("Fla. Stat. § 83.56", "Termination of rental agreement"),
    (
        "Fla. Stat. § 83.60",
        "Defenses to action for rent or possession; procedure",
    ),
)

EVICTION_CURATED_CITATIONS: dict[str, CitationResolution] = {
    normalize_citation(citation): CitationResolution(
        citation=citation,
        source_url=_CH_83_SOURCE_URL,
        section=citation.split("§")[-1].strip(),
        title=title,
    )
    for citation, title in _ENTRIES
}

# Verbatim list for the system prompt — the model must cite only from this set.
EVICTION_CITATION_LIST = [citation for citation, _title in _ENTRIES]
