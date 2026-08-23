"""I-8 — LLM-on-tap tests. The Anthropic client is mocked; the tests pin
the PROMPT CONTRACTS (no date math, no coverage decisions, no settlement
prediction), the JSON shape, citation filtering, and the provider-failure
path. No network calls. No pytest-asyncio in this repo — bodies run via
asyncio.run()."""

import asyncio
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.agents import pc_llm_tap


class FakeResponse:
    def __init__(self, text: str):
        self.content = [type("Block", (), {"text": text})()]


class FakeMessages:
    def __init__(self, response_text: str | None = None, error: Exception | None = None):
        self.response_text = response_text
        self.error = error
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return FakeResponse(self.response_text or "{}")


class FakeParser:
    async def extract_from_bytes_async(self, file_bytes):
        return {"raw_text": "This is a sample insurance letter about a claim."}


def _make_tap(monkeypatch, response_text=None, error=None):
    t = pc_llm_tap.PcLlmTap()
    fake = FakeMessages(response_text=response_text, error=error)
    monkeypatch.setattr(t.client, "messages", fake)
    t._pdf_parser = FakeParser()
    return t, fake


def _prompts():
    return [
        pc_llm_tap._SYSTEM_EXPLAIN_LETTER,
        pc_llm_tap._SYSTEM_DESCRIBE_ITEM,
        pc_llm_tap._SYSTEM_NOTES_TO_DEMAND,
        pc_llm_tap._SYSTEM_DEFINE_TERM,
        pc_llm_tap._SYSTEM_CLASSIFY_DOCUMENT,
    ]


def test_every_prompt_forbids_date_math():
    for prompt in _prompts():
        assert "NEVER compute" in prompt
        assert "NEVER decide whether a peril is covered" in prompt
        assert "NEVER predict" in prompt


def test_no_fake_statutes_in_prompts():
    for prompt in _prompts():
        assert "627.999" not in prompt


def test_describe_item_returns_inventory_row(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "room": "kitchen", "item": "toaster", "brand": "Cuisinart",
        "model": "", "serial": "", "qty": 1, "age_years": 3,
        "price_paid": "45", "condition": "good",
        "cost_new_today": "59.99", "price_source": "amazon.com",
    }))
    result = asyncio.run(t.describe_item("kitchen toaster cuisinart 3 years old paid 45"))
    assert result["item"] == "toaster"
    assert result["room"] == "kitchen"
    assert result["qty"] == 1


def test_define_term_filters_fabricated_citation(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "term": "ACV",
        "definition": "Actual cash value: what property was worth used at the time of loss.",
        "citations": ["Fla. Stat. § 627.999", "Fla. Stat. § 627.702"],
        "plain_language_note": "x",
    }))
    result = asyncio.run(t.define_term("ACV"))
    assert "627.999" not in json.dumps(result)
    assert "627.702" in json.dumps(result)


def test_provider_failure_returns_clean_error(monkeypatch):
    t, fake = _make_tap(monkeypatch, error=RuntimeError("boom"))
    result = asyncio.run(t.describe_item("notes"))
    assert result["error"] is True
    assert result["message"] == pc_llm_tap._PROVIDER_ERROR_MESSAGE


def test_unsupported_file_type_returns_error(monkeypatch):
    t, fake = _make_tap(monkeypatch)
    result = asyncio.run(t.explain_letter(b"xyz", "photo.xyz"))
    assert result["error"] is True
    assert "Unsupported file type" in result["message"]
    assert fake.calls == []  # no provider call for a bad file


def test_explain_letter_pdf_text_path(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "summary": "The insurer reserves rights.",
        "deadline_statements": [{"quote": "within 30 days", "note": "The letter states this window."}],
        "requests_of_reader": ["provide documents"],
        "type_guess": "reservation_of_rights_letter",
        "citations": [],
    }))
    result = asyncio.run(t.explain_letter(b"%PDF-1.4 fake", "letter.pdf"))
    assert result["summary"] == "The insurer reserves rights."
    assert fake.calls, "provider should have been called"
    system = fake.calls[0]["system"][0]["text"]
    assert "NEVER compute" in system


def test_classify_document_coerces_unknown_type(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "document_type": "not_a_real_type", "confidence": "high",
        "one_line_summary": "x", "citations": [],
    }))
    result = asyncio.run(t.classify_document(b"%PDF-1.4 fake", "doc.pdf"))
    assert result["document_type"] == "other"


def test_classify_document_keeps_valid_type(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "document_type": "denial_letter", "confidence": "medium",
        "one_line_summary": "x", "citations": [],
    }))
    result = asyncio.run(t.classify_document(b"%PDF-1.4 fake", "doc.pdf"))
    assert result["document_type"] == "denial_letter"


def test_notes_to_demand_returns_body(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text=json.dumps({
        "body": "Dear insurer, I write regarding claim number X.",
        "citations": [],
    }))
    result = asyncio.run(t.notes_to_demand("they underpaid the roof"))
    assert "Dear insurer" in result["body"]


def test_malformed_json_is_provider_failure(monkeypatch):
    t, fake = _make_tap(monkeypatch, response_text="not json at all {{{")
    result = asyncio.run(t.describe_item("notes"))
    assert result["error"] is True
