"""Unit tests for the deterministic URL/domain stripper — Decision 4 (B4d).

Pure Python — no LLM, no DB calls.

Run: cd backend && uv run pytest tests/test_url_filter.py -v
"""

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.url_filter import (
    StreamingURLFilter,
    strip_urls,
    strip_urls_final,
)
from src.agents.form_guide import FormGuideAgent
from src.agents.expungement import ExpungementAgent


# ── Known emitters (B4b-1a showed prompt edits cannot stop these) ────────────

def test_strips_clsmf_org():
    out = strip_urls_final("Free legal help is available at clsmf.org.", "explainer")
    assert "clsmf.org" not in out
    assert "Free legal help is available at" in out


def test_strips_myflcourtaccess_com():
    out = strip_urls_final("File your response at myflcourtaccess.com today.", "explainer")
    assert "myflcourtaccess.com" not in out
    assert "File your response at" in out


def test_strips_hallucinated_domain():
    out = strip_urls_final(
        "You can find more information at floridalegalhelpdesk.org.", "explainer"
    )
    assert "floridalegalhelpdesk.org" not in out
    assert "You can find more information at" in out


# ── Readability of the exact example from the task spec ─────────────────────

def test_mid_sentence_url_leaves_readable_sentence():
    out = strip_urls_final("Free help: floridalawhelp.org.", "explainer")
    assert "floridalawhelp.org" not in out
    assert out == "Free help:"


def test_mid_sentence_full_url_preserves_surrounding_words():
    out = strip_urls_final(
        "Visit https://www.example.com/help for more information about your case.",
        "explainer",
    )
    assert "example.com" not in out
    assert "Visit" in out
    assert "for more information about your case." in out
    assert "  " not in out  # no doubled space left behind


def test_bare_www_domain_stripped():
    out = strip_urls_final("Go to www.floridacourts.org for forms.", "explainer")
    assert "floridacourts.org" not in out
    assert "Go to" in out
    assert "for forms." in out


# ── False-positive guards — none of these should be touched ──────────────────

def test_statute_citation_not_stripped():
    text = "This deadline is governed by Fla. Stat. § 83.60(2)."
    assert strip_urls(text, "explainer") == text


def test_case_citation_not_stripped():
    text = "See Smith v. Jones, 123 So. 3d 456 (Fla. 2020), for the controlling rule."
    assert strip_urls(text, "explainer") == text


def test_am_pm_not_stripped():
    text = "The hearing is scheduled for 9:00 a.m. and recesses at 12:00 p.m."
    assert strip_urls(text, "explainer") == text


def test_us_constitution_not_stripped():
    text = "This right is protected under the U.S. Constitution."
    assert strip_urls(text, "explainer") == text


def test_decimal_not_stripped():
    text = "The filing fee is $3.14 per page under Rule 1.070."
    assert strip_urls(text, "explainer") == text


def test_eg_ie_vs_initials_not_stripped():
    text = "Some documents (e.g., a lease, i.e. a written agreement) list J. Smith vs. the landlord."
    assert strip_urls(text, "explainer") == text


# ── Logging assertion ─────────────────────────────────────────────────────

def test_logs_agent_name_and_stripped_value(caplog):
    with caplog.at_level(logging.WARNING, logger="legalclear.url_filter"):
        strip_urls("Contact us at clsmf.org for help.", "police_report_v2")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert "police_report_v2" in record.getMessage()
    assert "clsmf.org" in record.getMessage()


# ── Streaming buffer: URL split across chunk boundaries ──────────────────────

def test_streaming_filter_catches_url_split_across_chunks():
    f = StreamingURLFilter("explainer")
    out = ""
    out += f.feed("Visit clsmf")
    out += f.feed(".org for free help. ")
    out += f.feed("Thanks for reading.")
    out += f.flush()
    assert "clsmf.org" not in out
    assert "Visit" in out
    assert "Thanks for reading." in out


def test_streaming_filter_does_not_split_a_word_mid_release():
    f = StreamingURLFilter("explainer")
    out = f.feed("The quick brown ")
    out += f.feed("fox jumps")
    out += f.flush()
    assert out == "The quick brown fox jumps"


# ── Integration: non-streaming agent JSON output boundary (B4d wiring) ───────

class _FakeContentBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeContentBlock(text)]


class _FakeMessagesCreate:
    def __init__(self, text: str) -> None:
        self._text = text

    async def create(self, **kwargs):
        return _FakeResponse(self._text)


class _FakeCreateClient:
    def __init__(self, text: str) -> None:
        self.messages = _FakeMessagesCreate(text)


def test_form_guide_strips_url_from_guide_output():
    agent = FormGuideAgent.__new__(FormGuideAgent)
    agent.client = _FakeCreateClient(json.dumps({
        "form_overview": "Free help is available at clsmf.org.",
        "before_you_start": [],
        "sections": [],
        "where_to_file": {},
        "after_filing": [],
        "deadline_warning": None,
        "small_claims_hearing_tips": None,
    }))
    agent.model = "claude-sonnet-4-6"
    agent.forms_library = {}

    result = asyncio.run(agent.guide(document={"text": ""}, classification={}))

    assert "clsmf.org" not in result["form_overview"]


def test_form_guide_strips_url_from_answer_form_question():
    agent = FormGuideAgent.__new__(FormGuideAgent)
    agent.client = _FakeCreateClient("Visit myflcourtaccess.com for filing status.")
    agent.model = "claude-sonnet-4-6"

    result = asyncio.run(agent.answer_form_question(
        document={"text": ""}, classification={}, guide={},
        question="How do I file?", chat_history=[],
    ))

    assert "myflcourtaccess.com" not in result["answer"]


def test_expungement_strips_url_from_guide_output():
    agent = ExpungementAgent.__new__(ExpungementAgent)
    agent.client = _FakeCreateClient(json.dumps({
        "what_is_expungement": "See floridalegalhelpdesk.org for details.",
        "eligibility_overview": "",
        "before_you_start": [],
        "steps": [],
        "form_fields": [],
        "where_to_file": {},
        "after_filing": [],
        "what_changes_after": [],
        "what_does_not_change": [],
        "free_resources": [],
    }))
    agent.guide_model = "claude-sonnet-4-6"

    result = asyncio.run(agent.guide(document={"text": ""}, classification={}))

    assert "floridalegalhelpdesk.org" not in result["what_is_expungement"]


def test_expungement_strips_url_from_eligibility_output():
    agent = ExpungementAgent.__new__(ExpungementAgent)
    agent.client = _FakeCreateClient(json.dumps({
        "likely_eligible": True,
        "confidence": "medium",
        "reasoning": "Check clsmf.org for local rules.",
        "key_factors": [],
        "next_steps": [],
        "disclaimer": "",
    }))
    agent.eligibility_model = "claude-haiku-4-5-20251001"

    result = asyncio.run(agent.check_eligibility(
        jurisdiction="FL", offense_description="misdemeanor",
        years_since_offense=5,
    ))

    assert "clsmf.org" not in result["reasoning"]
