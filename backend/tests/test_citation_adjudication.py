"""Phase C2 — citation adjudication pins (deterministic shell + canned
actions; the LLM verdict is scripted, never real).

Pins:
  - SUPPORTED keeps the citation, records verdict + explanation
  - WRONG_SCOPE / CONTRADICTS → deterministic exact-text scrub + scope
    note; log status flips to scrubbed_<verdict>
  - LLM transport failure / HTTP error / unrecoverable JSON → citation
    STAYS, adjudication 'unavailable' (never stripped on a failed call)
  - zero Haiku calls when there is no API key or no verified citation
  - scrub_exact_citation never touches charges_explained[].charge

Pure Python — scripted requests.post, no DB, no LLM, no network.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

import pytest

from src.services import citation_adjudication
from src.services.citation_adjudication import adjudicate_verified_citations
from src.services.citation_validation import scrub_exact_citation


class _FakeResp:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self._text = text

    def json(self):
        return {"content": [{"text": self._text}]}


@pytest.fixture
def fake_post(monkeypatch):
    calls = []
    responses = []

    def _responder(*args, **kwargs):
        calls.append(kwargs["json"]["messages"][0]["content"])
        if not responses:
            raise AssertionError("fake_post: no scripted response left")
        return responses.pop(0)

    monkeypatch.setattr("requests.post", _responder)
    monkeypatch.setattr(
        citation_adjudication, "settings",
        SimpleNamespace(ANTHROPIC_API_KEY="test-key"),
    )
    return calls, responses


def _verified_entry(**overrides):
    entry = {
        "status": "verified",
        "citation": "Fla. Stat. § 893.13",
        "section": "893.13",
        "chapter": "893",
        "title": "Controlled substance possession",
        "statute_text": (
            "It is unlawful for any person to possess a controlled "
            "substance except as authorized."
        ),
        "context": "The charge under Fla. Stat. § 893.13 carries penalties.",
    }
    entry.update(overrides)
    return entry


def _analysis():
    return {
        "incident_summary": "A traffic stop occurred.",
        "charges_explained": [
            {"charge": "F.S. § 893.13(6)(a)", "plain_english": "possession"},
        ],
        "discrepancies": [
            {
                "severity": "high",
                "defect_category": "fourth_amendment",
                "description": (
                    "The charge under Fla. Stat. § 893.13 carries "
                    "penalties."
                ),
                "ask_attorney": "q?",
                "page_ref": "p.1",
            },
        ],
        "citation_notes": [],
    }


def _verdict_resp(verdict, explanation="explanation here"):
    return _FakeResp(
        text=f'{{"verdict": "{verdict}", "explanation": "{explanation}"}}',
    )


# ---------------------------------------------------------------------------
# Canned actions
# ---------------------------------------------------------------------------


def test_supported_keeps_citation_and_records(fake_post):
    calls, responses = fake_post
    responses.append(_verdict_resp("SUPPORTED"))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" in out["discrepancies"][0]["description"]
    assert log[0]["status"] == "verified"
    assert log[0]["adjudication"] == "SUPPORTED"
    assert log[0]["adjudication_explanation"] == "explanation here"
    assert len(calls) == 1
    assert "STATUTE TEXT" in calls[0]


def test_wrong_scope_strips_and_notes(fake_post):
    calls, responses = fake_post
    responses.append(_verdict_resp("WRONG_SCOPE"))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" not in out["discrepancies"][0]["description"]
    assert log[0]["status"] == "scrubbed_wrong_scope"
    assert log[0]["removed"] >= 1
    assert any(
        "does not support" in n for n in out["citation_notes"]
    )
    assert len(calls) == 1


def test_contradicts_strips_and_notes(fake_post):
    calls, responses = fake_post
    responses.append(_verdict_resp("CONTRADICTS"))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" not in out["discrepancies"][0]["description"]
    assert log[0]["status"] == "scrubbed_contradicts"
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Failure modes: citation always survives a failed call
# ---------------------------------------------------------------------------


def test_garbage_json_marks_unavailable_and_keeps(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text="I am not JSON."))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" in out["discrepancies"][0]["description"]
    assert log[0]["adjudication"] == "unavailable"
    assert out["citation_notes"] == []
    assert len(calls) == 1


def test_http_error_marks_unavailable_and_keeps(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(status_code=500, text="boom"))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" in out["discrepancies"][0]["description"]
    assert log[0]["adjudication"] == "unavailable"
    assert len(calls) == 1


def test_transport_exception_marks_unavailable_and_keeps(fake_post, monkeypatch):
    calls, _responses = fake_post

    def _boom(*args, **kwargs):
        calls.append("transport")
        raise TimeoutError("connect timeout")

    monkeypatch.setattr("requests.post", _boom)
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" in out["discrepancies"][0]["description"]
    assert log[0]["adjudication"] == "unavailable"
    assert len(calls) == 1


def test_invalid_verdict_marks_unavailable_and_keeps(fake_post):
    _calls, responses = fake_post
    responses.append(_verdict_resp("MAYBE"))
    analysis = _analysis()

    out, log = adjudicate_verified_citations(
        analysis, [_verified_entry()],
    )

    assert "Fla. Stat. § 893.13" in out["discrepancies"][0]["description"]
    assert log[0]["adjudication"] == "unavailable"


# ---------------------------------------------------------------------------
# Zero-call guards
# ---------------------------------------------------------------------------


def test_no_verified_entries_zero_calls(fake_post):
    calls, _responses = fake_post
    log = [{
        "status": "scrubbed_court_only",
        "citation": "Florida Statute 90.606",
        "section": "90.606",
    }]

    out, out_log = adjudicate_verified_citations(_analysis(), log)

    assert out is not None
    assert out_log == log
    assert len(calls) == 0


def test_no_api_key_zero_calls(fake_post, monkeypatch):
    calls, _responses = fake_post
    monkeypatch.setattr(
        citation_adjudication, "settings",
        SimpleNamespace(ANTHROPIC_API_KEY=""),
    )

    _out, _out_log = adjudicate_verified_citations(
        _analysis(), [_verified_entry()],
    )

    assert len(calls) == 0


def test_verified_without_text_or_context_zero_calls(fake_post):
    calls, _responses = fake_post
    entry = _verified_entry(statute_text="", context="")

    _out, _log = adjudicate_verified_citations(_analysis(), [entry])

    assert len(calls) == 0


# ---------------------------------------------------------------------------
# scrub helper
# ---------------------------------------------------------------------------


def test_scrub_exact_citation_never_touches_charges():
    analysis = {
        "charges_explained": [
            {"charge": "F.S. § 893.13(6)(a)", "plain_english": "x"},
        ],
        "discrepancies": [
            {"description": "Under F.S. § 893.13(6)(a), the officer erred.",
             "ask_attorney": ""},
        ],
        "citation_notes": [],
    }

    out, removed = scrub_exact_citation(
        analysis, "F.S. § 893.13(6)(a)", "scope note",
    )

    assert removed >= 1
    assert "893.13" not in out["discrepancies"][0]["description"]
    assert out["charges_explained"][0]["charge"] == "F.S. § 893.13(6)(a)"
    assert out["citation_notes"] == ["scope note"]
