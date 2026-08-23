"""Tests for the prose-level citation filter (Dispatch J4-1).

Pure Python — no network, no live Supabase calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS
from src.agents.pc_citations import PC_CURATED_CITATIONS
from src.agents.property_casualty import _filter_citation_json_strings
from src.agents.small_claims_citations import SMALL_CLAIMS_CURATED_CITATIONS
from src.core.citation_filter import (
    StreamingCitationFilter,
    filter_citations_text,
    register_agent_curated_set,
    register_rule_citations,
)

AGENT = "test-agent"

# 2026-08-23 ruling: every agent name must declare its curated set
# explicitly — no implicit union, no fallthrough. This test agent declares
# the legacy full union (the pre-ruling behavior it was written against).
register_agent_curated_set(
    AGENT,
    set(SMALL_CLAIMS_CURATED_CITATIONS)
    | set(EVICTION_CURATED_CITATIONS)
    | set(PC_CURATED_CITATIONS),
)


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


# ---------------------------------------------------------------------------

# Dispatch J4-3 — wills_trusts / property_casualty / chat_expert wiring
# ---------------------------------------------------------------------------
#
# wills_trusts.py and chat_expert.py wire StreamingCitationFilter directly
# into their SSE generators — same feed()/flush() shape already covered
# above (test_token_split_across_feed_chunk_boundaries and friends), and
# those generators require a live Anthropic stream to exercise end to end.
# The checker (scripts/verify_educational.py check 6, PROSE_FILTER_FILES)
# asserts each file imports citation_filter; that plus the shared
# StreamingCitationFilter tests above is the coverage for those two files.
#
# property_casualty.py additionally has a pure post-stream JSON helper,
# _filter_citation_json_strings, which is testable directly with no network.


def test_pc_json_strings_strips_fabricated_citation_in_nested_prose():
    parsed = {
        "what_this_is": "See Fla. Stat. § 83.999 for details.",
        "watch_out_for": [
            {"severity": "high", "description": "Cites Fla. Stat. § 83.999(2)."},
        ],
    }
    result = _filter_citation_json_strings(parsed, "property_casualty")
    assert "83.999" not in result["what_this_is"]
    assert "83.999" not in result["watch_out_for"][0]["description"]


def test_pc_json_strings_preserves_curated_citation():
    parsed = {"what_this_is": "Jurisdiction follows Fla. Stat. § 34.01."}
    result = _filter_citation_json_strings(parsed, "property_casualty")
    assert "Fla. Stat. § 34.01" in result["what_this_is"]


def test_pc_json_strings_does_not_touch_key_deadlines_governing_rule():
    """key_deadlines is code-declared (deadline/compute.py) and gets
    overwritten wholesale after this filter runs in the agent — but the
    helper itself is a generic recursive string filter, so a governing_rule
    string that happens to be an uncurated citation (e.g. "Fla. Stat. §
    627.428", not in the P&C curated set) would be stripped if it were ever
    passed through here. This documents why the agent code applies the
    filter BEFORE overwriting key_deadlines, never after.
    """
    parsed = {"key_deadlines": [{"governing_rule": "Fla. Stat. § 627.428"}]}
    result = _filter_citation_json_strings(parsed, "property_casualty")
    assert "627.428" not in result["key_deadlines"][0]["governing_rule"]

# Per-surface wiring smoke tests (Dispatch J4-2)
#
# These exercise the same StreamingCitationFilter/filter_citations_text
# primitives each surface wires in, without a live model or network call —
# each surface's own streaming generator requires an Anthropic API call to
# drive, so the wiring itself is covered by scripts/verify_educational.py
# check 6 (PROSE_FILTER_FILES) asserting the import is present.
# ---------------------------------------------------------------------------


def test_small_claims_stream_filter_strips_fabricated_citation():
    f = StreamingCitationFilter("small_claims")
    out = ""
    out += f.feed(
        "Small claims covers disputes up to $8,000. See Fla. Stat. § 83.999 "
        "for details on filing."
    )
    out += f.flush()
    assert "83.999" not in out
    assert "Small claims covers disputes up to $8,000" in out


def test_criminal_procedure_stream_filter_strips_fabricated_citation():
    f = StreamingCitationFilter("criminal_procedure")
    out = ""
    out += f.feed(
        "The arraignment stage is governed by Fla. Stat. § 999.001 in this "
        "example."
    )
    out += f.flush()
    assert "999.001" not in out
    assert "The arraignment stage" in out


def test_discovery_motion_stream_filter_strips_fabricated_citation():
    f = StreamingCitationFilter("discovery_motion")
    out = ""
    out += f.feed(
        "This motion is analyzed under Fla. Stat. § 999.220, a fabricated "
        "citation for this test."
    )
    out += f.flush()
    assert "999.220" not in out
    assert "This motion is analyzed under" in out


# ---------------------------------------------------------------------------
# Dispatch J5 — owned rule citations extend the resolution registry
# ---------------------------------------------------------------------------


def test_registered_rule_citation_survives():
    register_rule_citations(["Fla. R. Gen. Prac. & Jud. Admin. 2.514"])
    text = "Time is computed per Fla. R. Gen. Prac. & Jud. Admin. 2.514."
    result = filter_citations_text(text, AGENT)
    assert "Fla. R. Gen. Prac. & Jud. Admin. 2.514" in result


def test_criminal_procedure_rule_citation_survives_after_registration():
    register_rule_citations(["Fla. R. Crim. P. 3.220"])
    text = "Discovery is governed by Fla. R. Crim. P. 3.220."
    result = filter_citations_text(text, AGENT)
    assert "Fla. R. Crim. P. 3.220" in result


def test_unregistered_rule_citation_still_stripped():
    text = "This cites Fla. R. Crim. P. 3.999, which is fabricated."
    result = filter_citations_text(text, AGENT)
    assert "3.999" not in result


def test_register_rule_citations_is_idempotent():
    register_rule_citations(["Fla. R. Crim. P. 3.220"])
    register_rule_citations(["Fla. R. Crim. P. 3.220"])
    register_rule_citations(["Fla. R. Crim. P. 3.220"])
    text = "See Fla. R. Crim. P. 3.220 for discovery obligations."
    result = filter_citations_text(text, AGENT)
    assert "Fla. R. Crim. P. 3.220" in result


def test_statute_curated_citations_survive_after_rule_registration():
    register_rule_citations(["Fla. R. Gen. Prac. & Jud. Admin. 2.514"])
    text = "The court has jurisdiction. See Fla. Stat. § 34.01 for details."
    result = filter_citations_text(text, AGENT)
    assert "Fla. Stat. § 34.01" in result


def test_small_claims_structured_helper_strips_fabricated_citation():
    from src.agents.small_claims import _filter_citation_json_strings

    parsed = {
        "what_this_is": "Small claims court handles disputes up to $8,000.",
        "watch_out_for": ["Cite Fla. Stat. § 83.999 improperly."],
    }
    cleaned = _filter_citation_json_strings(parsed, "small_claims")
    assert "83.999" not in cleaned["watch_out_for"][0]
    assert "Small claims court handles disputes up to $8,000." == cleaned["what_this_is"]



# ── per-agent registry gate (2026-08-23, Joe ruling) ─────────────────────


def test_unregistered_agent_raises_loudly():
    """An agent name the guard does not know must FAIL, not silently emit
    unfiltered prose — the generalized form of the pc_llm_tap bug."""
    import pytest

    from src.core.citation_filter import _ensure_registry
    _ensure_registry()
    with pytest.raises(RuntimeError, match="has no curated-set registry entry"):
        filter_citations_text("See Fla. Stat. § 83.999.", "agent_never_registered")


def test_census_of_known_agents_all_registered():
    """Every agent name in production code must be in the registry."""
    from src.core.citation_filter import _ensure_registry
    _ensure_registry()
    census = [
        "explainer", "property_casualty", "small_claims",
        "criminal_procedure", "discovery_motion", "wills_trusts",
        "pc_llm_tap",
        "chat_expert:small_claims", "chat_expert:criminal_procedure",
        "chat_expert:police_report", "chat_expert:discovery_motion",
        "chat_expert:property_casualty", "chat_expert:wills_trusts",
        "chat_expert:landlord_tenant",
    ]
    for name in census:
        result = filter_citations_text("Ordinary prose with no citations.", name)
        assert result == "Ordinary prose with no citations.", name


def test_pc_llm_tap_is_pc_only_not_legacy_union():
    """pc_llm_tap declares the P&C set ONLY — an eviction citation that the
    legacy union would keep must be stripped for the tap, while a P&C
    citation survives."""
    from src.core.citation_filter import _ensure_registry
    _ensure_registry()
    eviction_cite = "See Fla. Stat. § 83.60 about the 5-day window."
    assert "83.60" in filter_citations_text(eviction_cite, "explainer")  # legacy union keeps it
    assert "83.60" not in filter_citations_text(eviction_cite, "pc_llm_tap")  # tap strips it
    pc_cite = "See Fla. Stat. § 627.70131 for the acknowledgment window."
    assert "627.70131" in filter_citations_text(pc_cite, "pc_llm_tap")
