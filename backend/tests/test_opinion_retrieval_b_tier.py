"""Phase B — case-law relevance hardening pins (2026-08-30 plan).

Pins, deterministically:
  - rows with an empty citation never surface (tag path, ILIKE path, Orin)
  - two-tier admission in fact mode: rows matching >=1 fact term are the
    ONLY tier whenever any exist; >=2 tag-term matches is the fallback
  - ranking: fact_matched DESC, tag_matched DESC, overlap DESC, cite DESC
  - legacy mode (no analysis_result) keeps overlap-first ranking
  - the attorney-question prompt carries the discrepancy description and
    the grounding rule

Pure Python — scripted fake Supabase client, no DB, no LLM, no network.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

import pytest

from src.services import opinion_retrieval, orin_opinions
from src.services.opinion_retrieval import (
    generate_attorney_questions,
    get_relevant_opinions,
)


def _row(case_name, summary="", cite_count=0, situation_tags=None,
         citation="1 Fla. L. Weekly 1"):
    return {
        "case_name": case_name,
        "citation": citation,
        "court": "Fla. Dist. Ct. App.",
        "date_filed": "2020-01-01",
        "cite_count": cite_count,
        "outcome": "",
        "summary_plain": summary,
        "summary_legal": "",
        "attorney_prompt": "",
        "situation_tags": situation_tags,
        "cluster_id": f"cluster-{case_name}",
    }


class _FakeQuery:
    def __init__(self, client):
        self._client = client
        self._mode = None

    def select(self, *a, **k):
        return self

    def overlaps(self, *a, **k):
        self._mode = "tag"
        return self

    def or_(self, filter_string, *a, **k):
        self._mode = "ilike"
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        rows = self._client.ilike_rows if self._mode == "ilike" \
            else self._client.tag_rows
        return type("_Result", (), {"data": rows})()


class _FakeClient:
    def __init__(self, tag_rows=None, ilike_rows=None):
        self.tag_rows = list(tag_rows or [])
        self.ilike_rows = list(ilike_rows or [])

    def table(self, *a, **k):
        return _FakeQuery(self)


@pytest.fixture
def fake_db(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(opinion_retrieval.db, "client", client)
    monkeypatch.setattr(
        orin_opinions, "search_orin_opinions", lambda *a, **k: [],
    )
    return client


def _herrera_v2() -> dict:
    """Report facts that derive known fact terms (deterministic)."""
    return {
        "miranda_noted": False,
        "probable_cause_present": None,
        "charges_explained": [
            {"charge": "Possession", "plain_english": "a misdemeanor"},
        ],
        "discrepancies": [
            {
                "severity": "high",
                "defect_category": "fourth_amendment",
                "description": (
                    "Consent to search was coerced; the Terry stop was "
                    "predicated on an anonymous tip of undetermined "
                    "reliability."
                ),
                "ask_attorney": "Was the stop lawful?",
                "page_ref": "p.1",
            },
            {
                "severity": "high",
                "defect_category": "miranda",
                "description": (
                    "The Miranda warning was read in English despite a "
                    "language barrier; no interpreter was provided."
                ),
                "ask_attorney": "Was the waiver valid?",
                "page_ref": "p.2",
            },
        ],
        "missing_fields": [],
        "what_happens_next": "review",
    }


def _tags() -> list[str]:
    return [
        "fifth_amendment", "fourth_amendment", "language_access",
        "sixth_amendment", "unlawful_search", "misdemeanor",
    ]


# ---------------------------------------------------------------------------
# Empty-citation drop
# ---------------------------------------------------------------------------


def test_empty_citation_dropped_tag_and_ilike(fake_db):
    fake_db.tag_rows = [
        _row("State v. Tracey", "cell-site warrant case", 53,
             ["fourth_amendment"], citation=""),
        _row("State v. Placeholder", "consent to search case", 40,
             ["fourth_amendment"], citation="N/A"),
        _row("State v. Good", "consent to search after terry stop", 20,
             ["fourth_amendment"]),
    ]
    fake_db.ilike_rows = [
        _row("State v. EmptyToo", "miranda warning and language barrier",
             30, citation=""),
        _row("State v. NullToo", "terry stop based on a citizen tip",
             25, citation="null"),
    ]
    out = get_relevant_opinions(_tags(), 3, _herrera_v2())
    names = [o["case_name"] for o in out]
    assert "State v. Tracey" not in names
    assert "State v. EmptyToo" not in names
    assert "State v. Placeholder" not in names  # 'N/A' is not a citation
    assert "State v. NullToo" not in names      # 'null' is not a citation
    assert names  # the good row survives


def test_empty_citation_dropped_in_legacy_mode(fake_db):
    fake_db.tag_rows = [
        _row("State v. Tracey", "cell-site warrant case", 53,
             ["fourth_amendment"], citation=""),
        _row("State v. Good", "fourth amendment search", 20,
             ["fourth_amendment"]),
    ]
    out = get_relevant_opinions(_tags(), 3)  # no analysis_result
    names = [o["case_name"] for o in out]
    assert "State v. Tracey" not in names
    assert "State v. Good" in names


# ---------------------------------------------------------------------------
# Two-tier admission
# ---------------------------------------------------------------------------


def test_fact_tier_excludes_tag_only_rows(fake_db):
    fake_db.tag_rows = [
        _row("State v. FactTagged",
             "warrantless consent to search followed a terry stop and an "
             "anonymous tip; miranda warning omitted", 10,
             ["fourth_amendment"]),
        _row("State v. TagOnly",
             "the fourth amendment and sixth amendment were argued", 500,
             ["fourth_amendment", "sixth_amendment"]),
    ]
    fake_db.ilike_rows = [
        _row("State v. FactIlike",
             "language barrier with no interpreter at the miranda warning",
             5),
        _row("State v. Noise", "some case about amendments", 999),
    ]
    out = get_relevant_opinions(_tags(), 3, _herrera_v2())
    names = [o["case_name"] for o in out]
    assert "State v. TagOnly" not in names  # tag-only tier excluded
    assert "State v. Noise" not in names
    assert "State v. FactTagged" in names
    assert "State v. FactIlike" in names


def test_tag_tier_fallback_when_zero_fact_matches(fake_db):
    fake_db.tag_rows = [
        _row("State v. TagTwo",
             "fourth amendment and sixth amendment questions were decided",
             40, ["fourth_amendment", "sixth_amendment"]),
        _row("State v. TagOne",
             "a fourth amendment question was decided", 60,
             ["fourth_amendment"]),
    ]
    fake_db.ilike_rows = []
    out = get_relevant_opinions(_tags(), 3, _herrera_v2())
    names = [o["case_name"] for o in out]
    assert "State v. TagTwo" in names    # >=2 tag terms: fallback tier
    assert "State v. TagOne" not in names  # <2 tag terms: no signal


def test_fact_ranking_fact_then_tag_then_cite(fake_db):
    fake_db.tag_rows = [
        _row("State v. WeakFact",
             "a miranda warning was given", 900,
             ["fifth_amendment"]),          # fact=1
        _row("State v. StrongFact",
             "miranda warning, language barrier, and consent to search "
             "issues", 5, ["fifth_amendment"]),  # fact=3+
        _row("State v. MidFact",
             "miranda warning with a language barrier", 100,
             ["fifth_amendment"]),          # fact=2
    ]
    fake_db.ilike_rows = []
    out = get_relevant_opinions(_tags(), 3, _herrera_v2())
    names = [o["case_name"] for o in out]
    assert names[0] == "State v. StrongFact"
    assert names[1] == "State v. MidFact"
    assert names[2] == "State v. WeakFact"
    assert out[0]["cite_count"] == 5  # cite_count never outranks facts


# ---------------------------------------------------------------------------
# Attorney-question grounding
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self._text = text

    def json(self):
        return {"content": [{"text": self._text}]}


def test_attorney_prompt_carries_description_and_grounding(monkeypatch):
    calls = []

    def _responder(*args, **kwargs):
        calls.append(kwargs["json"]["messages"][0]["content"])
        return _FakeResp(
            text='[{"explanation":"e1","question":"q1"}]',
        )

    monkeypatch.setattr("requests.post", _responder)
    monkeypatch.setattr(
        opinion_retrieval, "settings",
        SimpleNamespace(ANTHROPIC_API_KEY="test-key"),
    )
    opinions = [_row("State v. FactTagged", "consent to search summary", 10)]

    out = generate_attorney_questions(_herrera_v2(), opinions)

    assert len(calls) == 1
    prompt = calls[0]
    assert "Consent to search was coerced" in prompt  # description reached
    assert "GROUNDING RULE" in prompt
    assert out[0]["attorney_prompt"] == "q1"
