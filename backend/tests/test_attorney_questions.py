"""Unit tests for the Haiku attorney-questions repair (2026-08-27).

Locks the AGENTS.md JSON discipline in generate_attorney_questions:
  - markdown fences stripped via the shared json_utils path
  - trailing prose / embedded array recovered deterministically (largest [..])
  - exactly ONE LLM retry, only on parse failure (not transport / non-200)
  - graceful degradation: opinions returned unchanged, never raises
  - legacy plain-string items still map to question-only

Pure Python — mocked requests.post, no DB, no LLM, no network.
Run: cd backend && uv run python -m pytest tests/test_attorney_questions.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

import pytest

from src.core.json_utils import parse_json_array, parse_json_list
from src.services import opinion_retrieval
from src.services.opinion_retrieval import generate_attorney_questions

# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def _opinions(n=3):
    return [
        {
            "case_name": f"State v. Person{i}",
            "citation": f"1 Fla. L. Weekly {i}",
            "court": "Fla. Dist. Ct. App.",
            "summary_plain": "plain summary",
            "attorney_prompt": "generic prompt",
        }
        for i in range(n)
    ]


def _analysis():
    return {
        "discrepancies": [
            {"description": "Miranda violation", "ask_attorney": "whether statement is suppressible"}
        ],
        "charges_explained": [{"charge": "Burglary"}],
    }


class _FakeResp:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self._text = text

    def json(self):
        return {"content": [{"text": self._text}]}


@pytest.fixture
def fake_post(monkeypatch):
    """Patch requests.post with a scriptable responder; records prompts."""
    calls = []
    responses = []

    def _responder(*args, **kwargs):
        calls.append(kwargs["json"]["messages"][0]["content"])
        if not responses:
            raise AssertionError("fake_post: no scripted response left")
        return responses.pop(0)

    monkeypatch.setattr("requests.post", _responder)
    monkeypatch.setattr(
        opinion_retrieval, "settings", SimpleNamespace(ANTHROPIC_API_KEY="test-key")
    )
    return calls, responses


# ---------------------------------------------------------------------------
# deterministic recovery paths (no retry needed)
# ---------------------------------------------------------------------------

def test_valid_array_enriches(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text='[{"explanation":"e1","question":"q1"},{"explanation":"e2","question":"q2"}]'))
    opinions = _opinions(2)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_explanation"] == "e1"
    assert out[0]["attorney_prompt"] == "q1"
    assert out[1]["attorney_prompt"] == "q2"
    assert len(calls) == 1  # no retry on success


def test_fenced_json_recovers(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text='```json\n[{"explanation":"e1","question":"q1"}]\n```'))
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "q1"
    assert len(calls) == 1


def test_trailing_prose_recovers(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(
        text="Here are the questions you asked for:\n"
        '[{"explanation":"e1","question":"q1"}]\n'
        "I hope this helps with the case."
    ))
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "q1"
    assert len(calls) == 1


def test_legacy_plain_string_maps_to_question_only(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text='["plain question one"]'))
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "plain question one"
    assert out[0]["attorney_explanation"] == ""
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# retry-once semantics
# ---------------------------------------------------------------------------

def test_parse_failure_retries_once_and_recovers(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text="I'm sorry, I cannot produce that right now."))
    responses.append(_FakeResp(text='[{"explanation":"e1","question":"q1"}]'))
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "q1"
    assert len(calls) == 2
    assert "IMPORTANT" in calls[1]  # tightened instruction on the retry


def test_both_parse_failures_degrade_to_unchanged(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(text="total gibberish, not json at all"))
    responses.append(_FakeResp(text="still not json, sorry"))
    opinions = _opinions(2)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out is opinions
    assert out[0]["attorney_prompt"] == "generic prompt"
    assert len(calls) == 2  # exactly one retry, never more


def test_http_error_degrades_without_retry(fake_post):
    calls, responses = fake_post
    responses.append(_FakeResp(status_code=500, text="boom"))
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "generic prompt"
    assert len(calls) == 1  # non-200 is not retryable


def test_transport_exception_degrades_without_retry(fake_post, monkeypatch):
    calls, _responses = fake_post

    def _boom(*args, **kwargs):
        calls.append("transport")
        raise TimeoutError("connect timeout")

    monkeypatch.setattr("requests.post", _boom)
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out[0]["attorney_prompt"] == "generic prompt"
    assert len(calls) == 1  # transport failure is not retryable


# ---------------------------------------------------------------------------
# guards
# ---------------------------------------------------------------------------

def test_no_key_no_calls(fake_post, monkeypatch):
    monkeypatch.setattr(opinion_retrieval, "settings", SimpleNamespace(ANTHROPIC_API_KEY=""))
    calls, _responses = fake_post
    opinions = _opinions(1)

    out = generate_attorney_questions(_analysis(), opinions)

    assert out is opinions
    assert len(calls) == 0


def test_no_opinions_no_calls(fake_post):
    calls, _responses = fake_post

    out = generate_attorney_questions(_analysis(), [])

    assert out == []
    assert len(calls) == 0


# ---------------------------------------------------------------------------
# json_utils refactor regression guards
# ---------------------------------------------------------------------------

def test_parse_json_array_returns_none_on_failure():
    assert parse_json_array("no json here") is None


def test_parse_json_list_still_drops_non_dicts():
    assert parse_json_list('[{"a":1},"str",2]') == [{"a": 1}]
