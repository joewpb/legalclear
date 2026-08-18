"""Tests for the small-claims curated citation pilot (Dispatch J2).

Pure Python — no network, no live Supabase calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.small_claims import SmallClaimsExplainer, SYSTEM_PROMPT
from src.agents.small_claims_citations import (
    SMALL_CLAIMS_CITATION_LIST,
    SMALL_CLAIMS_CURATED_CITATIONS,
)
from src.core.citation_resolver import resolve_citation


def test_every_curated_citation_resolves():
    for citation in SMALL_CLAIMS_CITATION_LIST:
        result = resolve_citation(citation, SMALL_CLAIMS_CURATED_CITATIONS)
        assert result is not None, f"{citation} failed to resolve"
        assert result.citation == citation
        assert result.source_url.startswith("https://www.leg.state.fl.us/")
        assert result.title


def test_curated_set_has_seventeen_entries():
    assert len(SMALL_CLAIMS_CITATION_LIST) == 17
    assert len(SMALL_CLAIMS_CURATED_CITATIONS) == 17


def test_fabricated_citation_is_stripped():
    payload = [
        {"section": "what_this_is", "citation": "Fla. Stat. § 34.01"},
        {"section": "typical_timeline", "citation": "Fla. Stat. § 34.999"},
    ]
    filtered = SmallClaimsExplainer.filter_citations(payload)
    assert len(filtered) == 1
    assert filtered[0]["citation"] == "Fla. Stat. § 34.01"


def test_rules_7x_citation_is_stripped():
    payload = [{"section": "watch_out_for", "citation": "Fla. Sm. Cl. R. 7.050"}]
    filtered = SmallClaimsExplainer.filter_citations(payload)
    assert filtered == []


def test_non_ch34_owned_citation_is_stripped():
    """A real statute outside the curated ch. 34 subset must not pass."""
    payload = [{"section": "what_this_is", "citation": "Fla. Stat. § 83.60"}]
    filtered = SmallClaimsExplainer.filter_citations(payload)
    assert filtered == []


def test_malformed_citations_payload_does_not_raise():
    assert SmallClaimsExplainer.filter_citations(None) == []
    assert SmallClaimsExplainer.filter_citations("not a list") == []
    assert SmallClaimsExplainer.filter_citations([{"no_citation_key": True}]) == []
    assert SmallClaimsExplainer.filter_citations(["not a dict"]) == []


def test_prompt_instructs_cite_only_from_curated_set():
    lowered = SYSTEM_PROMPT.lower()
    assert "cite only" in lowered or "only the following" in lowered
    assert "never invent" in lowered
    for citation in SMALL_CLAIMS_CITATION_LIST:
        assert citation in SYSTEM_PROMPT


def test_prompt_develops_filing_and_not_filing_branches_honestly():
    """AGENTS 2d: both the filing and not-filing branches must be
    developed, including the case where not filing is reasonable
    (amount below the cost of pursuing the claim)."""
    lowered = SYSTEM_PROMPT.lower()
    assert "if the person files" in lowered
    assert "if the person does not file" in lowered
    assert "enforced" in lowered  # filing branch: judgment enforcement
    assert "statute of limitations" in lowered  # not-filing branch
    assert "reasonable choice" in lowered  # honest not-filing branch


def test_prompt_uses_conditional_framing_not_bare_directives():
    lowered = SYSTEM_PROMPT.lower()
    assert "if the" in lowered
    assert "you should" not in lowered
    assert "you must" not in lowered
    assert "do this" not in lowered
