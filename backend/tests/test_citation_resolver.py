"""Tests for the citation resolution guard (Dispatch J1).

Pure Python — no network, no live Supabase calls. Fixtures only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.citation_resolver import (
    CitationResolution,
    load_owned_citations,
    normalize_citation,
    resolve_citation,
    resolve_citations,
)

FIXTURE_OWNED = {
    normalize_citation("Fla. Stat. § 34.01"): CitationResolution(
        citation="Fla. Stat. § 34.01",
        source_url="https://www.leg.state.fl.us/statutes/34.01",
        section="34.01",
        title="Jurisdiction of county court",
    ),
    normalize_citation("Fla. Stat. § 83.60"): CitationResolution(
        citation="Fla. Stat. § 83.60",
        source_url="https://www.leg.state.fl.us/statutes/83.60",
        section="83.60",
        title="Defenses; failure to pay rent",
    ),
    normalize_citation("Fla. R. Civ. P. 1.140"): CitationResolution(
        citation="Fla. R. Civ. P. 1.140",
        source_url="https://www.floridabar.org/rules/1.140",
        section="1.140",
        title="Defenses",
    ),
}


def test_valid_ch34_cite_resolves():
    result = resolve_citation("Fla. Stat. § 34.01", FIXTURE_OWNED)
    assert result is not None
    assert result.citation == "Fla. Stat. § 34.01"
    assert result.section == "34.01"


def test_unowned_rules_7x_cite_suppressed():
    result = resolve_citation("Fla. Sm. Cl. R. 7.050", FIXTURE_OWNED)
    assert result is None


def test_fabricated_cite_suppressed():
    result = resolve_citation("Fla. Stat. § 34.999", FIXTURE_OWNED)
    assert result is None


def test_normalization_variants_resolve():
    assert resolve_citation("fla. stat.   s.34.01", FIXTURE_OWNED) is not None
    assert resolve_citation("§ 34.01", FIXTURE_OWNED) is not None
    result_a = resolve_citation("fla. stat.   s.34.01", FIXTURE_OWNED)
    result_b = resolve_citation("§ 34.01", FIXTURE_OWNED)
    assert result_a.citation == result_b.citation == "Fla. Stat. § 34.01"


def test_empty_map_suppresses_everything_no_exception():
    assert resolve_citation("Fla. Stat. § 34.01", {}) is None
    assert resolve_citations(["Fla. Stat. § 34.01", "Fla. Stat. § 83.60"], {}) == []


def test_resolve_citations_dedupes_and_preserves_order():
    citations = [
        "Fla. R. Civ. P. 1.140",
        "Fla. Stat. § 34.01",
        "Fla. Stat. § 34.01",
        "Fla. Sm. Cl. R. 7.050",
        "Fla. Stat. § 83.60",
    ]
    resolved = resolve_citations(citations, FIXTURE_OWNED)
    assert [r.citation for r in resolved] == [
        "Fla. R. Civ. P. 1.140",
        "Fla. Stat. § 34.01",
        "Fla. Stat. § 83.60",
    ]


def test_load_owned_citations_no_client_returns_empty_map():
    class _DegradedDB:
        client = None

    assert load_owned_citations(_DegradedDB()) == {}


def test_load_owned_citations_none_db_returns_empty_map():
    assert load_owned_citations(None) == {}


def test_load_owned_citations_query_failure_returns_empty_map_no_exception():
    class _BoomTable:
        def select(self, *_args, **_kwargs):
            raise RuntimeError("network unavailable in tests")

    class _BoomClient:
        def table(self, _name):
            return _BoomTable()

    class _BoomDB:
        client = _BoomClient()

    assert load_owned_citations(_BoomDB()) == {}
