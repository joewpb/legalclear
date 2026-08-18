"""Tests for the prose-level citation filter (Dispatch J4-1).

Pure Python — no network, no live Supabase calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.citation_filter import StreamingCitationFilter, filter_citations_text

AGENT = "test-agent"


def test_curated_citation_survives_verbatim():
    text = "The court has jurisdiction. See Fla. Stat. § 34.01 for details."
    result = filter_citations_text(text, AGENT)
    assert "Fla. Stat. § 34.01" in result


def test_fabricated_citation_stripped():
    text = "The tenant may raise a defense under Fla. Stat. § 83.999."
    result = filter_citations_text(text, AGENT)
    assert "83.999" not in result


def test_real_but_uncurated_citation_stripped():
    text = "Repairs are covered by Fla. Stat. § 83.64 in some cases."
    result = filter_citations_text(text, AGENT)
    assert "83.64" not in result


def test_subsection_of_curated_base_survives():
    text = "The landlord must respond per Fla. Stat. § 83.60(2)."
    result = filter_citations_text(text, AGENT)
    assert "Fla. Stat. § 83.60(2)" in result


def test_subsection_of_fabricated_base_stripped():
    text = "This cites Fla. Stat. § 83.999(2) as its basis."
    result = filter_citations_text(text, AGENT)
    assert "83.999" not in result


def test_token_split_across_feed_chunk_boundaries():
    f = StreamingCitationFilter(AGENT)
    out = ""
    out += f.feed("The landlord must respond per Fla. Stat. § 83.")
    out += f.feed("999 within the statutory period.")
    out += f.flush()
    assert "83.999" not in out
    assert "within the statutory period" in out


def test_curated_citation_survives_across_chunk_boundaries():
    f = StreamingCitationFilter(AGENT)
    out = ""
    out += f.feed("See Fla. Stat. § 34.")
    out += f.feed("01 for jurisdiction.")
    out += f.flush()
    assert "Fla. Stat. § 34.01" in out


def test_non_citation_prose_untouched():
    text = "The § symbol in a contract."
    result = filter_citations_text(text, AGENT)
    assert result == text
