"""Dispatch G1 — citation filter regex extension.

Tests the phrasings the models are known to actually produce (collected in
``tests/fixtures/citation_phrasings.jsonl`` via
``scripts/collect_citation_phrasings.py``) plus the explicit acceptance
cases from the dispatch. Pure Python — no network, no live Supabase calls.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.citation_filter import (
    filter_citations_text,
    register_agent_curated_set,
)

AGENT = "test-agent"

# Self-contained registration (2026-08-27): this file previously relied on
# test_citation_filter.py's module-level register_agent_curated_set("test-agent")
# running first — order-dependent coupling. Targeted runs (this file alone)
# therefore hit the registry's raise-on-unknown path and failed 12/12 while
# full-suite runs passed silently. Register here so the tests stand alone.
from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS
from src.agents.pc_citations import PC_CURATED_CITATIONS
from src.agents.small_claims_citations import (
    SMALL_CLAIMS_CURATED_CITATIONS,
)

register_agent_curated_set(
    AGENT,
    set(SMALL_CLAIMS_CURATED_CITATIONS)
    | set(EVICTION_CURATED_CITATIONS)
    | set(PC_CURATED_CITATIONS),
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "citation_phrasings.jsonl"


def _load_fixture_rows():
    if not FIXTURE_PATH.exists():
        raise AssertionError(
            "citation_phrasings fixture missing: "
            f"{FIXTURE_PATH} — the 46 live-collected phrasings are committed "
            "and must be present; a missing fixture means a broken checkout "
            "or a bad merge, never a silent skip."
        )
    rows = []
    with FIXTURE_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def test_fixture_phrasings_match_expected_classification():
    """Every distinct phrasing collected from a live run of each prose
    surface must be handled per its (best-effort) curated/uncurated
    classification: curated survives verbatim, uncurated is gone from the
    filtered output. Skips gracefully if the fixture hasn't been generated
    in this environment (no live LLM access).
    """
    rows = _load_fixture_rows()
    if not rows:
        return
    for row in rows:
        phrasing = row["phrasing"]
        result = filter_citations_text(phrasing, AGENT)
        if row["classification"] == "curated":
            assert phrasing in result, f"expected curated phrasing to survive: {phrasing!r}"
        else:
            assert phrasing not in result, f"expected uncurated phrasing to be stripped: {phrasing!r}"


# ---------------------------------------------------------------------------
# Explicit acceptance cases from the dispatch
# ---------------------------------------------------------------------------


def test_spelled_out_singular_uncurated_stripped():
    text = "This claim relates to Florida Statute 626.9541 concerning unfair methods."
    result = filter_citations_text(text, AGENT)
    assert "626.9541" not in result


def test_spelled_out_singular_curated_survives():
    text = "The insurer's duty is governed by Florida Statute 627.70131."
    result = filter_citations_text(text, AGENT)
    assert "Florida Statute 627.70131" in result


def test_section_of_florida_statutes_trailing_form_stripped():
    text = "This is prohibited under section 626.9541, Florida Statutes."
    result = filter_citations_text(text, AGENT)
    assert "626.9541" not in result


def test_fs_abbreviation_curated_survives():
    text = "Under F.S. 627.70131 the insurer must act promptly."
    result = filter_citations_text(text, AGENT)
    assert "F.S. 627.70131" in result


def test_admin_code_rule_form_stripped():
    text = "See Fla. Admin. Code Rule 69O-166.031 for the applicable standard."
    result = filter_citations_text(text, AGENT)
    assert "69O-166.031" not in result


def test_florida_administrative_code_rule_spelled_out_stripped():
    text = "The Florida Administrative Code Rule 69O-166.031 sets the standard."
    result = filter_citations_text(text, AGENT)
    assert "69O-166.031" not in result


def test_fac_abbreviation_stripped():
    text = "F.A.C. 69O-166.031 governs claims handling standards."
    result = filter_citations_text(text, AGENT)
    assert "69O-166.031" not in result


def test_bare_number_adjacent_to_florida_statutes_stripped():
    text = "The relevant provision is found in Florida Statutes, specifically 626.9541 nearby."
    result = filter_citations_text(text, AGENT)
    assert "626.9541" not in result


def test_fabricated_spelled_out_citation_stripped():
    text = "This is governed by Florida Statute 627.999, which does not exist."
    result = filter_citations_text(text, AGENT)
    assert "627.999" not in result


def test_fla_stats_plural_abbreviation_curated_survives():
    text = "Fla. Stats. 627.70131 requires prompt acknowledgment."
    result = filter_citations_text(text, AGENT)
    assert "Fla. Stats. 627.70131" in result


def test_section_of_the_florida_statutes_curated_survives():
    text = "This is addressed by section 627.70131 of the Florida Statutes."
    result = filter_citations_text(text, AGENT)
    assert "627.70131" in result
