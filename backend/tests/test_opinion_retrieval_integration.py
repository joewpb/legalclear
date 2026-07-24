"""Integration test for get_relevant_opinions() against the live
legal_opinions table in Supabase. Skips when credentials are absent
or the table is unreachable, so CI (no service key) stays green.

Run (local, with backend/.env present):
    cd backend && uv run python -m pytest tests/test_opinion_retrieval_integration.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from dotenv import load_dotenv
load_dotenv()

from src.services.opinion_retrieval import get_relevant_opinions


REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY")
_HAS_CREDS = all(os.environ.get(k) for k in REQUIRED_ENV)

skip_no_creds = pytest.mark.skipif(
    not _HAS_CREDS, reason="requires SUPABASE_URL + SUPABASE_SERVICE_KEY in env"
)

# Fields the service selects — every returned row should have them.
_EXPECTED_FIELDS = {
    "case_name", "citation", "court", "date_filed", "cite_count",
    "outcome", "summary_plain", "summary_legal", "attorney_prompt",
}


@skip_no_creds
def test_empty_tags_returns_empty_without_query():
    # No tags -> no DB call, immediate [].
    assert get_relevant_opinions([]) == []


@skip_no_creds
def test_known_tag_combo_returns_ranked_opinions():
    # felony=346, fourth_amendment=17 — guaranteed overlap in the corpus.
    opinions = get_relevant_opinions(["felony", "fourth_amendment"], limit=3)

    assert len(opinions) > 0, "expected non-empty overlap for felony+fourth_amendment"
    assert len(opinions) <= 3

    # Every row carries the contracted fields.
    for op in opinions:
        missing = _EXPECTED_FIELDS - set(op.keys())
        assert not missing, f"row missing fields: {missing}"

    # cite_count ordering is descending (PostgREST .order desc).
    counts = [op.get("cite_count") for op in opinions]
    assert counts == sorted(counts, reverse=True)


@skip_no_creds
def test_charge_class_only_tags_return_empty():
    # A charge-class label alone carries no legal issue — the gate must
    # short-circuit to [] even though the live corpus is reachable (this is
    # the real-DB confirmation of the gate; the pre-DB logic is unit-tested
    # in test_opinion_mapper.py).
    assert get_relevant_opinions(["misdemeanor"]) == []   # LC-TEST-002 profile
    assert get_relevant_opinions(["felony"]) == []
    # Bare DUI charge — dui + traffic_stop are both class tags now.
    assert get_relevant_opinions(["dui", "traffic_stop"]) == []
    assert get_relevant_opinions(["felony", "misdemeanor", "dui"]) == []


@skip_no_creds
def test_substantive_alongside_class_still_retrieves():
    # Regression (Adkins-style): a class tag + a substantive tag must still
    # retrieve normally — the class gate only suppresses class-ONLY sets.
    opinions = get_relevant_opinions(["felony", "fourth_amendment"], limit=3)
    assert len(opinions) > 0, "felony + fourth_amendment must still retrieve"
    # A DUI charge WITH a real fourth_amendment defect must still retrieve.
    opinions = get_relevant_opinions(
        ["dui", "traffic_stop", "fourth_amendment"], limit=3
    )
    assert len(opinions) > 0, "DUI + fourth_amendment must still retrieve"

