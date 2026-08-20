"""Tests for the Property & Casualty curated citation set (Dispatch I-1).

Pure Python — no network, no live Supabase calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.pc_citations import PC_CITATION_LIST
from src.agents.property_casualty import (
    _BAD_FAITH_PREMISES_SYSTEM_PROMPT,
    _FIRST_PARTY_SYSTEM_PROMPT,
)
from src.core.citation_filter import filter_citations_text

AGENT = "property_casualty"

# Snapshot of the frozen bad_faith/premises prompt at dispatch time — this
# prompt must NOT change as part of this dispatch.
_FROZEN_PROMPT_LENGTH = 1502
_FROZEN_PROMPT_HASH = hash(_BAD_FAITH_PREMISES_SYSTEM_PROMPT)


def test_every_curated_citation_survives_filter():
    for citation in PC_CITATION_LIST:
        text = f"The claim process is governed by {citation}."
        result = filter_citations_text(text, AGENT)
        assert citation in result, f"{citation} was stripped"


def test_fabricated_ch627_citation_stripped():
    text = "This is supported by Fla. Stat. § 627.999, a fabricated section."
    result = filter_citations_text(text, AGENT)
    assert "627.999" not in result


def test_real_but_uncurated_citation_stripped():
    # § 627.428 (attorney fees) is owned in prod statutes but NOT in the
    # P&C curated set — must still be stripped.
    text = "Prevailing insureds may recover fees under Fla. Stat. § 627.428."
    result = filter_citations_text(text, AGENT)
    assert "627.428" not in result


def test_first_party_prompt_has_cite_from_set_instruction():
    prompt = _FIRST_PARTY_SYSTEM_PROMPT
    assert "curated set" in prompt
    assert "Never cite outside the owned corpus" in prompt
    assert "never invent a citation" in prompt


def test_first_party_prompt_has_no_date_arithmetic_marker():
    prompt = _FIRST_PARTY_SYSTEM_PROMPT
    assert "Never compute" in prompt
    assert "NEVER compute, derive, or modify a deadline date" in prompt


def test_bad_faith_premises_prompt_is_unchanged():
    assert len(_BAD_FAITH_PREMISES_SYSTEM_PROMPT) == _FROZEN_PROMPT_LENGTH
    assert hash(_BAD_FAITH_PREMISES_SYSTEM_PROMPT) == _FROZEN_PROMPT_HASH
