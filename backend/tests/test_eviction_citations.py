"""Tests for the eviction curated citation set and explainer union wiring
(Dispatch J3).

Pure Python — no network, no live Supabase calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.eviction_citations import (
    EVICTION_CITATION_LIST,
    EVICTION_CURATED_CITATIONS,
)
from src.agents.explainer import ExplainerAgent, SYSTEM_PROMPT
from src.agents.small_claims_citations import SMALL_CLAIMS_CITATION_LIST
from src.core.citation_resolver import resolve_citation


def test_every_curated_citation_resolves():
    for citation in EVICTION_CITATION_LIST:
        result = resolve_citation(citation, EVICTION_CURATED_CITATIONS)
        assert result is not None, f"{citation} failed to resolve"
        assert result.citation == citation
        assert result.source_url.startswith("https://www.leg.state.fl.us/")
        assert result.title


def test_curated_set_has_exactly_three_entries():
    assert len(EVICTION_CITATION_LIST) == 3
    assert len(EVICTION_CURATED_CITATIONS) == 3


def test_83_60_subsection_2_is_not_a_curated_entry():
    """Subsection-level granularity is code-declared in the deadline
    engine's governing_rule, never model-emitted — it has no place here."""
    assert "Fla. Stat. § 83.60(2)" not in EVICTION_CITATION_LIST
    assert resolve_citation(
        "Fla. Stat. § 83.60(2)", EVICTION_CURATED_CITATIONS
    ) is None


def test_fabricated_ch83_citation_is_stripped():
    payload = [{"section": "summary", "citation": "Fla. Stat. § 83.999"}]
    filtered = ExplainerAgent.filter_citations(payload)
    assert filtered == []


def test_real_but_uncurated_ch83_citation_is_stripped():
    """§ 83.64 is a real ch. 83 section but not in the curated set."""
    payload = [{"section": "summary", "citation": "Fla. Stat. § 83.64"}]
    filtered = ExplainerAgent.filter_citations(payload)
    assert filtered == []


def test_union_includes_eviction_and_small_claims():
    payload = [
        {"section": "summary", "citation": "Fla. Stat. § 83.49"},
        {"section": "summary", "citation": "Fla. Stat. § 34.01"},
    ]
    filtered = ExplainerAgent.filter_citations(payload)
    citations = {item["citation"] for item in filtered}
    assert "Fla. Stat. § 83.49" in citations
    assert "Fla. Stat. § 34.01" in citations
    assert len(filtered) == 2


def test_prompt_instructs_cite_only_from_union_set():
    lowered = SYSTEM_PROMPT.lower()
    assert "cite only" in lowered or "only the following" in lowered
    assert "never invent" in lowered
    for citation in EVICTION_CITATION_LIST:
        assert citation in SYSTEM_PROMPT
    for citation in SMALL_CLAIMS_CITATION_LIST:
        assert citation in SYSTEM_PROMPT
