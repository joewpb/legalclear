"""Small Claims curated citation set (Dispatch J2 — pilot of the curated-set
pattern, ch. 34 ONLY).

These are the ONLY citations the small-claims explainer may emit. Each entry
was verified by the orchestrator against prod (citation -> row lookup -> text
present -> source_url on leg.state.fl.us) before being pinned here. This is a
strict subset of the owned ``statutes`` rows loaded by
``core.citation_resolver.load_owned_citations`` — never a superset.

``source_url`` follows the same chapter-page pattern used by
``scripts/ingest_statutes.py`` (``chapter_url()``): every section in ch. 34
shares one Display_Statute URL, since FL Statutes source pages are chapter-
level, not per-section.
"""

from __future__ import annotations

from src.core.citation_resolver import CitationResolution, normalize_citation

_CH_34_SOURCE_URL = (
    "https://www.leg.state.fl.us/statutes/index.cfm"
    "?App_mode=Display_Statute&URL=0000-0099/0034/0034.html"
)

_ENTRIES = (
    ("Fla. Stat. § 34.01", "Jurisdiction of county court"),
    ("Fla. Stat. § 34.011", "Jurisdiction in landlord and tenant cases"),
    ("Fla. Stat. § 34.017", "Certification of questions"),
    ("Fla. Stat. § 34.021", "Qualifications of county court judges"),
    ("Fla. Stat. § 34.022", "Number of judges"),
    ("Fla. Stat. § 34.031", "Clerk"),
    ("Fla. Stat. § 34.032", "Power of clerk to appoint deputies"),
    ("Fla. Stat. § 34.041", "Filing fees"),
    ("Fla. Stat. § 34.045", "Cost recovery"),
    ("Fla. Stat. § 34.07", "Sheriff"),
    ("Fla. Stat. § 34.08", "Compensation of sheriff"),
    ("Fla. Stat. § 34.13", "Method of prosecution"),
    ("Fla. Stat. § 34.131", "Voluntary pleas of guilty"),
    ("Fla. Stat. § 34.161", "48 hours to pay fines"),
    ("Fla. Stat. § 34.171", "Salaries of bailiffs"),
    ("Fla. Stat. § 34.181", "Branch courts"),
    ("Fla. Stat. § 34.191", "Fines and forfeitures"),
)

SMALL_CLAIMS_CURATED_CITATIONS: dict[str, CitationResolution] = {
    normalize_citation(citation): CitationResolution(
        citation=citation,
        source_url=_CH_34_SOURCE_URL,
        section=citation.split("§")[-1].strip(),
        title=title,
    )
    for citation, title in _ENTRIES
}

# Verbatim list for the system prompt — the model must cite only from this set.
SMALL_CLAIMS_CITATION_LIST = [citation for citation, _title in _ENTRIES]
