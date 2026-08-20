"""Property & Casualty curated citation set (Dispatch I-1 — module authority
list, base citations ONLY).

These are the ONLY citations the property_casualty first-party explainer may
emit in prose. Each entry was verified by the orchestrator against prod
(citation -> row lookup -> text present -> source_url on leg.state.fl.us)
before being pinned here. This is a strict subset of the owned ``statutes``
rows loaded by ``core.citation_resolver.load_owned_citations`` — never a
superset.

BASE CITATIONS ONLY: no subsection-suffixed entries (e.g. "Fla. Stat. §
95.11(2)(e)" is NOT pinned here as its own key — "Fla. Stat. § 95.11" is, and
the filter's base-citation-lookup rule (see ``core.citation_filter``) lets a
subsection suffix on that base survive verbatim).

Unlike ch. 83 and ch. 34 (single chapter-level source page), ch. 627's FL
Statutes source pages are per-section, so each entry carries its own
``source_url`` rather than one shared chapter URL.
"""

from __future__ import annotations

from src.core.citation_resolver import CitationResolution, normalize_citation

_ENTRIES = (
    (
        "Fla. Stat. § 627.70131",
        "Insurer's duty to acknowledge and act promptly upon claims",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.70131.html",
    ),
    (
        "Fla. Stat. § 627.70132",
        "Notice of claim",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.70132.html",
    ),
    (
        "Fla. Stat. § 627.7011",
        "Homeowners' policies; scope of policy; replacement costs; "
        "matching of undamaged property",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.7011.html",
    ),
    (
        "Fla. Stat. § 627.702",
        "Total loss of building or mobile home; effect of coinsurance "
        "clause on total losses; valued policy law",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.702.html",
    ),
    (
        "Fla. Stat. § 627.7015",
        "Alternative procedure for resolution of disputed property "
        "insurance claims",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.7015.html",
    ),
    (
        "Fla. Stat. § 627.70152",
        "Suits arising under a property insurance policy; presuit notice",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.70152.html",
    ),
    (
        "Fla. Stat. § 627.7152",
        "Assignment agreements",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.7152.html",
    ),
    (
        "Fla. Stat. § 627.7142",
        "Homeowner Claims Bill of Rights",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.7142.html",
    ),
    (
        "Fla. Stat. § 627.706",
        "Sinkhole and catastrophic ground cover collapse insurance; "
        "standards for claims determination",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.706.html",
    ),
    (
        "Fla. Stat. § 627.7074",
        "Alternative procedure for resolution of disputed sinkhole "
        "insurance claims",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0627/Sections/0627.7074.html",
    ),
    (
        "Fla. Stat. § 95.11",
        "Limitations other than for the recovery of real property",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&URL=0000-0099/0095/0095.html",
    ),
    (
        "Fla. Stat. § 624.155",
        "Civil remedy",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0624/Sections/0624.155.html",
    ),
    (
        "Fla. Stat. § 626.854",
        "Public adjusters",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0600-0699/0626/Sections/0626.854.html",
    ),
    (
        "Fla. Stat. § 718.111",
        "The association",
        "https://www.leg.state.fl.us/statutes/index.cfm"
        "?App_mode=Display_Statute&Search_String=&URL=0700-0799/0718/Sections/0718.111.html",
    ),
)

PC_CURATED_CITATIONS: dict[str, CitationResolution] = {
    normalize_citation(citation): CitationResolution(
        citation=citation,
        source_url=source_url,
        section=citation.split("§")[-1].strip(),
        title=title,
    )
    for citation, title, source_url in _ENTRIES
}

# Verbatim list for the system prompt — the model must cite only from this set.
PC_CITATION_LIST = [citation for citation, _title, _url in _ENTRIES]
