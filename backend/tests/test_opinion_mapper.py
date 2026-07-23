"""Unit tests for derive_situation_tags() — the Police Report V2 ->
situation_tags mapper. Pure Python — no LLM, no DB calls.

Run: cd backend && uv run python -m pytest tests/test_opinion_mapper.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.services.opinion_retrieval import derive_situation_tags


def _v2(**overrides) -> dict:
    """A clean V2 result with no triggering signals; override per test."""
    base = {
        "miranda_noted": True,        # explicit True -> NOT a violation
        "probable_cause_present": True,
        "charges_explained": [],
        "discrepancies": [],
        "missing_fields": [],
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("v2_result, expected", [
    # 1. Miranda violation via the curated boolean.
    (_v2(miranda_noted=False), ["fifth_amendment", "sixth_amendment"]),
    # 2. Miranda defect via structured defect_category — fires even though
    #    miranda_noted is True (the default). The category is the PRIMARY
    #    signal and is independent of the boolean state.
    (_v2(discrepancies=[{
        "severity": "high",
        "defect_category": "miranda",
        "description": "Officer never gave a Miranda warning before questioning.",
        "ask_attorney": "Was this custodial?", "page_ref": "p.2",
    }]), ["fifth_amendment", "sixth_amendment"]),
    # 2b. Miranda described ONLY in prose, with no defect_category and the
    #     boolean True, still does NOT tag — free-text alone never fires
    #     (precision preserved on the prose path).
    (_v2(discrepancies=[{
        "severity": "high",
        "description": "Officer never gave a Miranda warning before questioning.",
        "ask_attorney": "Was this custodial?", "page_ref": "p.2",
    }]), []),
    # 2c. Fourth-Amendment defect via category (no boolean signal).
    (_v2(discrepancies=[{
        "severity": "high",
        "defect_category": "fourth_amendment",
        "description": "Vehicle searched without consent or probable cause.",
        "ask_attorney": "Basis for the search?", "page_ref": "p.1",
    }]), ["fourth_amendment", "probable_cause", "unlawful_search"]),
    # 2d. Due-process defect via category — emits due_process tag (note:
    #     not yet present in the FL-only corpus, so retrieval is empty
    #     until a corpus-scope decision; mapper behavior is what's tested).
    (_v2(discrepancies=[{
        "severity": "high",
        "defect_category": "due_process",
        "description": "Defendant denied opportunity to review evidence.",
        "ask_attorney": "", "page_ref": None,
    }]), ["due_process"]),
    # 2e. Language-access defect via category.
    (_v2(discrepancies=[{
        "severity": "medium",
        "defect_category": "language_access",
        "description": "No interpreter offered to LEP subject during interview.",
        "ask_attorney": "", "page_ref": None,
    }]), ["language_access"]),
    # 2f. defect_category + boolean combine and dedupe (both point at
    #     Miranda; the resulting tag set is still just the two amendments).
    (_v2(miranda_noted=False, discrepancies=[{
        "severity": "high",
        "defect_category": "miranda",
        "description": "No Miranda warning.", "ask_attorney": "", "page_ref": None,
    }]), ["fifth_amendment", "sixth_amendment"]),
    # 3. Felony via stem match on "Burglary" (plain_english blank on purpose).
    (_v2(charges_explained=[
        {"charge": "Armed Burglary of a Dwelling", "plain_english": ""}]),
        ["felony"]),
    # 4. Robbery stem -> felony.
    (_v2(charges_explained=[
        {"charge": "Robbery with a Firearm", "plain_english": ""}]),
        ["felony"]),
    # 5. DUI -> dui + traffic_stop.
    (_v2(charges_explained=[
        {"charge": "DUI", "plain_english": ""}]),
        ["dui", "traffic_stop"]),
    # 6. Drug trafficking — stem "Trafficking" + substance "Cocaine".
    (_v2(charges_explained=[
        {"charge": "Trafficking in Cocaine (28g+)", "plain_english": ""}]),
        ["drug_trafficking"]),
    # 7. Possession alone is NOT trafficking -> no drug tag (precision).
    (_v2(charges_explained=[
        {"charge": "Possession of a controlled substance", "plain_english": ""}]),
        []),
    # 8. Probable-cause boolean False -> the unlawful_search signal path.
    (_v2(probable_cause_present=False),
        ["fourth_amendment", "probable_cause", "unlawful_search"]),
    # 9. Excessive force in discrepancy text -> police_misconduct.
    (_v2(discrepancies=[{
        "severity": "high",
        "description": "Taser used repeatedly after subject was restrained.",
        "ask_attorney": "", "page_ref": None,
    }]), ["police_misconduct"]),
    # 10. NEGATIVE: bare "search" in neutral narration -> no 4A tag.
    (_v2(discrepancies=[{
        "severity": "low",
        "description": "Report notes officers conducted a search of the "
                       "vehicle and found nothing; no discrepancy in the "
                       "search itself, timestamp is missing.",
        "ask_attorney": "", "page_ref": None,
    }]), []),
    # 11. No matching signals -> [] (precision: no baseline tag).
    (_v2(), []),
    # 12. Null booleans are NOT violations (null != False).
    (_v2(miranda_noted=None, probable_cause_present=None), []),
    # 13. LLM-JSON drift: string "false"/"False" still counts as negation.
    (_v2(miranda_noted="false", probable_cause_present="False"),
        ["fifth_amendment", "fourth_amendment",
         "probable_cause", "sixth_amendment", "unlawful_search"]),
    # 14. Simple assault is a misdemeanor in FL — bare "assault" must NOT
    #     trigger the felony tag (precision regression fixed).
    (_v2(charges_explained=[
        {"charge": "Simple Assault", "plain_english": ""}]),
        []),
    # 15. Aggravated assault IS a felony and is still caught by the qualifier.
    (_v2(charges_explained=[
        {"charge": "Aggravated Assault with a Deadly Weapon", "plain_english": ""}]),
        ["felony"]),
])
def test_derive_situation_tags(v2_result, expected):
    assert derive_situation_tags(v2_result) == expected


def test_derive_non_dict_returns_empty():
    assert derive_situation_tags(None) == []          # type: ignore[arg-type]
    assert derive_situation_tags("not a dict") == []  # type: ignore[arg-type]
