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
    # 8. probable_cause_present == False alone does NOT fire 4A tags. The
    #    boolean means "no PC affidavit in the paperwork," not "a search
    #    occurred without valid PC" — a summons-only report with no search
    #    can legitimately lack one. 4A coverage is owned by defect_category.
    (_v2(probable_cause_present=False), []),
    # 8b. REGRESSION: the Faketown/Doe disorderly-conduct profile — a
    #     summons-only charge (misdemeanor), no search/seizure, PC
    #     affidavit absent (paperwork gap), no fourth_amendment defect —
    #     must produce NO 4A/unlawful_search/probable_cause tags.
    (_v2(
        probable_cause_present=False,
        charges_explained=[
            {"charge": "Disorderly Conduct", "plain_english": ""}],
        discrepancies=[{
            "severity": "medium",
            "defect_category": "procedural",
            "description": "No probable-cause affidavit attached to the report.",
            "ask_attorney": "", "page_ref": None,
        }],
    ), []),
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
    # 13. LLM-JSON drift: string "false"/"False" still counts as Miranda
    #     negation. probable_cause_present="False" no longer contributes
    #     (boolean→4A mapping removed); only the Miranda boolean path fires.
    (_v2(miranda_noted="false", probable_cause_present="False"),
        ["fifth_amendment", "sixth_amendment"]),
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


# ---------------------------------------------------------------------------
# Charge-class gate on get_relevant_opinions(). These are PURE unit tests — no
# Supabase credentials required — so they run in CI. They prove the gate fires
# *before* any DB round-trip (otherwise a class-only set would be impossible to
# distinguish from degraded-mode []). Strategy: monkeypatch the module-level
# `db.client` with sentinels that detect / explode on `.table()`.
# ---------------------------------------------------------------------------

import src.services.opinion_retrieval as opinion_retrieval  # noqa: E402
import src.services.orin_opinions as orin_opinions  # noqa: E402
from src.services.opinion_retrieval import get_relevant_opinions  # noqa: E402


class _ExplodingClient:
    """DB client whose .table() raises — proves the gate short-circuits
    before any query for charge-class-only tag sets."""

    def table(self, *args, **kwargs):  # noqa: ANN001
        raise AssertionError(
            "db.client.table() was called — the charge-class gate should "
            "have short-circuited before any DB work"
        )


class _RecordingClient:
    """DB client whose query chain records that .table() was reached and
    returns an empty result set. Proves substantive tag sets are NOT
    short-circuited by the gate. Carries the full chain surface
    (select/overlaps/eq/or_/order/limit) so the retrieval service's
    tag-overlap and ILIKE queries both traverse cleanly."""

    queried = False

    def table(self, *args, **kwargs):  # noqa: ANN001
        type(self).queried = True
        return self

    def select(self, *args, **kwargs):  # noqa: ANN001
        return self

    def overlaps(self, *args, **kwargs):  # noqa: ANN001
        return self

    def or_(self, *args, **kwargs):  # noqa: ANN001
        return self

    def order(self, *args, **kwargs):  # noqa: ANN001
        return self

    def eq(self, *args, **kwargs):  # noqa: ANN001
        return self

    def limit(self, *args, **kwargs):  # noqa: ANN001
        return self

    def execute(self):  # noqa: ANN201
        return type("_Result", (), {"data": []})()


def test_class_only_tags_return_empty_without_db_call(monkeypatch):
    # A charge-class label alone (no substantive tag) must short-circuit to
    # [] WITHOUT touching the DB. Verified by patching in a client that
    # explodes if .table() is reached.
    monkeypatch.setattr(opinion_retrieval.db, "client", _ExplodingClient())
    # LC-TEST-002 profile: misdemeanor tag alone.
    assert get_relevant_opinions(["misdemeanor"]) == []
    # Felony tag alone.
    assert get_relevant_opinions(["felony"]) == []
    # Bare DUI charge — dui + traffic_stop (both auto-emitted, both class).
    assert get_relevant_opinions(["dui", "traffic_stop"]) == []
    # Multiple class tags, still no substantive tag.
    assert get_relevant_opinions(["felony", "misdemeanor", "dui"]) == []


def test_substantive_tag_set_is_not_gated(monkeypatch):
    # Regression: a substantive tag (here fourth_amendment) alongside a
    # class tag must pass through the gate and reach the DB query — the
    # Adkins-style felony + fourth_amendment match must keep working.
    _RecordingClient.queried = False
    monkeypatch.setattr(opinion_retrieval.db, "client", _RecordingClient())
    # Orin fallback (added in 1335d88) must return [] in unit tests —
    # otherwise real Supabase/Orin results leak through when the
    # recording client's empty result triggers the fallback path.
    monkeypatch.setattr(orin_opinions, "search_orin_opinions", lambda *a, **kw: [])
    opinions = get_relevant_opinions(["felony", "fourth_amendment"])
    assert _RecordingClient.queried is True, (
        "expected the query to run for a substantive tag set; the gate "
        "must not short-circuit when a substantive tag is present"
    )
    assert opinions == []  # empty corpus result from the recording client
