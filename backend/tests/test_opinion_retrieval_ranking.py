"""Unit tests for the police-report case-law relevance fix
(2026-08): fact-term extraction, relevance ranking, junk-row filtering,
and preservation of the legacy tag-overlap-first path.

Pure Python — a scripted fake Supabase client, no DB, no LLM.
Run: cd backend && uv run python -m pytest tests/test_opinion_retrieval_ranking.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import src.services.opinion_retrieval as opinion_retrieval
import src.services.orin_opinions as orin_opinions
from src.services.opinion_retrieval import (
    _derive_fact_terms,
    _merge_search_terms,
    get_relevant_opinions,
)


_OPINION_COLUMNS_KEYS = {
    "case_name", "citation", "court", "date_filed", "cite_count",
    "outcome", "summary_plain", "summary_legal", "attorney_prompt",
}


def _row(case_name, summary="", cite_count=0, situation_tags=None):
    return {
        "case_name": case_name,
        "citation": "1 Fla. L. Weekly 1",
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


# ---------------------------------------------------------------------------
# Scripted fake Supabase client: .overlaps() -> tag rows, .or_() -> ilike rows
# ---------------------------------------------------------------------------


class _FakeQuery:
    def __init__(self, client):
        self._client = client
        self._mode = None

    def select(self, *args, **kwargs):  # noqa: ANN001
        return self

    def overlaps(self, *args, **kwargs):  # noqa: ANN001
        self._mode = "tag"
        return self

    def or_(self, filter_string, *args, **kwargs):  # noqa: ANN001
        self._mode = "ilike"
        self._client.captured_filters.append(filter_string)
        if any(f in filter_string for f in self._client.fail_filters):
            raise RuntimeError(f"injected anchor failure: {filter_string}")
        return self

    def eq(self, *args, **kwargs):  # noqa: ANN001
        return self

    def order(self, *args, **kwargs):  # noqa: ANN001
        return self

    def limit(self, *args, **kwargs):  # noqa: ANN001
        return self

    def execute(self):  # noqa: ANN201
        rows = (
            self._client.ilike_rows
            if self._mode == "ilike"
            else self._client.tag_rows
        )
        return type("_Result", (), {"data": rows})()


class _FakeClient:
    def __init__(self, tag_rows=None, ilike_rows=None, fail_filters=None):
        self.tag_rows = list(tag_rows or [])
        self.ilike_rows = list(ilike_rows or [])
        self.captured_filters = []
        # Substrings of or_ filters that should raise — simulates the
        # Supabase statement timeout on rare anchors.
        self.fail_filters = set(fail_filters or [])

    def table(self, *args, **kwargs):  # noqa: ANN001
        return _FakeQuery(self)


class _ExplodingClient:
    """Client whose .table() raises — proves a gate fires before any DB work."""

    def table(self, *args, **kwargs):  # noqa: ANN001
        raise AssertionError("db.client.table() was called — gate did not fire")


@pytest.fixture
def fake_db(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(opinion_retrieval.db, "client", client)
    # Orin fallback must return [] in unit tests — otherwise real
    # Supabase/Orin results leak through when the fake corpus is short.
    monkeypatch.setattr(orin_opinions, "search_orin_opinions", lambda *a, **k: [])
    return client


# ---------------------------------------------------------------------------
# Fact-term extraction
# ---------------------------------------------------------------------------


def _herrera_v2() -> dict:
    """LC-TEST-001 profile: Miranda / language-access / 4A-consent /
    Terry-stop defects, rich discrepancy prose."""
    return {
        "miranda_noted": False,
        "probable_cause_present": None,
        "charges_explained": [
            {
                "charge": "Possession of a Controlled Substance",
                "plain_english": "a misdemeanor drug possession charge",
            }
        ],
        "discrepancies": [
            {
                "severity": "high",
                "defect_category": "miranda",
                "description": (
                    "No Miranda warning was documented and no waiver of "
                    "rights was signed; the custodial interrogation was "
                    "conducted without an interpreter despite a language "
                    "barrier between the officer and the subject."
                ),
                "ask_attorney": "Was the waiver knowing and voluntary?",
                "page_ref": "p.2",
            },
            {
                "severity": "high",
                "defect_category": "fourth_amendment",
                "description": (
                    "The vehicle was searched after a Terry stop based on "
                    "an anonymous tip; consent to search was obtained under "
                    "coercive framing after the subject was handcuffed."
                ),
                "ask_attorney": "Was the consent voluntary?",
                "page_ref": "p.1",
            },
        ],
        "missing_fields": [
            {
                "severity": "medium",
                "field_name": "interpreter waiver form",
                "why_important": "shows whether the waiver of rights was "
                                 "knowing given the language barrier",
                "page_ref": None,
            }
        ],
    }


def test_derive_fact_terms_herrera_profile():
    terms = _derive_fact_terms(_herrera_v2())
    # Core phrases from the diagnosis proof must be present.
    for expected in (
        "consent to search", "terry stop", "anonymous tip",
        "language barrier", "waiver of rights", "custodial interrogation",
    ):
        assert expected in terms, f"missing fact term {expected!r}: {terms!r}"
    # Strong unigrams too.
    for expected in ("interpreter", "miranda", "consent", "handcuffed"):
        assert expected in terms, f"missing unigram {expected!r}: {terms!r}"
    # Shape invariants: lowercase, deduped, capped, bounded length.
    assert terms == list(dict.fromkeys(terms))
    assert all(t == t.lower() and t.strip() and len(t) <= 40 for t in terms)
    assert len(terms) <= 40


def test_derive_fact_terms_empty_inputs():
    assert _derive_fact_terms({}) == []
    assert _derive_fact_terms(None) == []          # type: ignore[arg-type]
    assert _derive_fact_terms("not a dict") == []  # type: ignore[arg-type]
    # Only neutral prose (no legal signal) -> no phrases, bigrams gated out.
    assert _derive_fact_terms({
        "discrepancies": [{"description": "The officer wrote the report.", "ask_attorney": ""}],
        "missing_fields": [],
        "charges_explained": [],
    }) == []


def test_merge_search_terms_facts_first_deduped_casefold():
    merged = _merge_search_terms(
        ["consent to search", "probable cause"],
        ["Probable Cause", "fourth amendment", "misdemeanor"],
    )
    assert merged == ["consent to search", "probable cause",
                      "fourth amendment", "misdemeanor"]


def test_fact_terms_from_missing_fields_and_charges():
    terms = _derive_fact_terms({
        "discrepancies": [],
        "missing_fields": [
            {"field_name": "interpreter", "why_important": "language barrier"}
        ],
        "charges_explained": [
            {"charge": "DUI", "plain_english": "driving under the influence"}
        ],
    })
    assert "interpreter" in terms
    assert "language barrier" in terms


# ---------------------------------------------------------------------------
# Relevance ranking (fact mode)
# ---------------------------------------------------------------------------


def test_fact_mode_ranks_relevant_above_famous_and_drops_junk(fake_db):
    fake_db.tag_rows = []
    fake_db.ilike_rows = [
        # Highly relevant: matches many fact terms.
        _row("Jardines v. State", cite_count=38, summary=(
            "Police used a drug dog at the front door after an anonymous "
            "tip. The court held that consent to search the curtilage had "
            "not been given and probable cause was lacking; the warrantless "
            "search was unlawful."
        )),
        # Famous murder case: matches one term only.
        _row("Murder v. Famous", cite_count=151, summary=(
            "Defendant convicted of first-degree murder; the court found "
            "probable cause for the arrest."
        )),
        # Matches only the charge-class term 'misdemeanor' — no substantive
        # match, must be dropped in fact mode.
        _row("Misdemeanor Only", cite_count=99, summary=(
            "The defendant was charged with misdemeanor possession."
        )),
        # Junk row: empty case_name, must never surface.
        _row("", cite_count=5, summary=(
            "consent to search probable cause terry stop"
        )),
        # No match at all (defensive; a real ILIKE result always matched
        # something, but a row matching only scrubbed noise must drop).
        _row("No Match Case", cite_count=200, summary="unrelated text"),
    ]
    tags = ["fourth_amendment", "probable_cause", "misdemeanor"]
    opinions = get_relevant_opinions(
        tags, limit=3, analysis_result=_herrera_v2(),
    )
    names = [o["case_name"] for o in opinions]
    # Relevance ranking: the fact-rich consent case wins.
    assert names[0] == "Jardines v. State", names
    # Charge-context exclusion (Joe ruling 2026-08-27): the murder case is
    # EXCLUDED for a report with no homicide charge — even though it ranked.
    assert "Murder v. Famous" not in names, names
    assert "Misdemeanor Only" not in names
    assert "No Match Case" not in names
    assert all(o["case_name"] for o in opinions), "junk rows leaked"
    # API shape unchanged: exactly the _OPINION_COLUMNS keys.
    for op in opinions:
        assert set(op.keys()) == _OPINION_COLUMNS_KEYS, set(op.keys())


def test_fact_mode_tag_rows_rank_by_text_matches(fake_db):
    # Tag path returns famous tagged cases with LOW fact-term matches and
    # the ILIKE path returns a fact-rich consent case. Facts win.
    fake_db.tag_rows = [
        _row("Tagged Murder", cite_count=120, situation_tags=[
            "fourth_amendment", "probable_cause",
        ], summary="probable cause for the murder arrest existed."),
    ]
    fake_db.ilike_rows = [
        _row("Bustamonte v. State", cite_count=30, summary=(
            "consent to search the vehicle was given; the court examined "
            "whether consent was voluntary under the totality of the "
            "circumstances and probable cause was not required."
        )),
    ]
    opinions = get_relevant_opinions(
        ["fourth_amendment", "probable_cause"],
        limit=3,
        analysis_result=_herrera_v2(),
    )
    names = [o["case_name"] for o in opinions]
    # Bustamonte matches consent-to-search + probable cause + consent +
    # terry-stop fact terms; the tagged murder case matches far fewer.
    assert names[0] == "Bustamonte v. State", names


def test_fact_mode_filter_uses_anchor_term_only(fake_db):
    # The fact-mode ILIKE queries are SINGLE-anchor filters chosen from the
    # measured-fast priority list (multi-term ORs of rare terms exceed the
    # Supabase statement timeout — verified 57014). Tag names and non-anchor
    # fact terms stay OUT of the OR-filter; they still count when ranking
    # candidates in Python. Junk-only results ADVANCE to the next anchor
    # (Joe ruling 2026-08-27), so all three anchor candidates get queried
    # when the corpus has nothing for any of them — each still a single term.
    fake_db.tag_rows = []
    fake_db.ilike_rows = []
    get_relevant_opinions(
        ["fourth_amendment", "probable_cause", "misdemeanor"],
        limit=3,
        analysis_result=_herrera_v2(),
    )
    assert len(fake_db.captured_filters) == 3, (
        f"expected 3 single-anchor queries (junk advancement), got "
        f"{fake_db.captured_filters}"
    )
    for i, expected_anchor in enumerate(
        ("language barrier", "interpreter", "anonymous tip")
    ):
        filt = fake_db.captured_filters[i]
        assert expected_anchor in filt, f"anchor {i} wrong: {filt!r}"
        # Single term per query: exactly one ilike clause.
        assert filt.count(".ilike.") == 1, f"multi-term filter: {filt!r}"
        for excluded in ("probable cause", ".consent%", ".terry stop%",
                         "fourth amendment"):
            assert excluded not in filt, f"term leaked into filter: {excluded!r}"


def test_fact_mode_anchor_retry_on_timeout_and_advance_below_threshold(fake_db):
    # A rare anchor can hit the Supabase statement timeout under load — the
    # service must fall through to the next anchor in priority order
    # (exception retry). A successful query returning only ONE usable row
    # (< _ANCHOR_MIN_USABLE_ROWS) must also advance (below-threshold rule,
    # Joe ruling 2026-08-27) — so anchor 1 fails, anchor 2 is thin, anchor 3
    # runs too; the single real row from anchor 2 still reaches the pool.
    fake_db.fail_filters = {"language barrier"}
    fake_db.tag_rows = []
    fake_db.ilike_rows = [
        _row("Interpreter Case", cite_count=10, summary=(
            "interpreter language barrier miranda rights waiver of rights"
        )),
    ]
    opinions = get_relevant_opinions(
        ["fifth_amendment", "language_access"], limit=3,
        analysis_result=_herrera_v2(),
    )
    assert len(fake_db.captured_filters) == 3, \
        f"expected fail + below-threshold advancement, got {fake_db.captured_filters}"
    assert "language barrier" in fake_db.captured_filters[0]
    assert "interpreter" in fake_db.captured_filters[1]
    assert "anonymous tip" in fake_db.captured_filters[2]
    assert opinions[0]["case_name"] == "Interpreter Case"


def test_pool_anchor_terms_selection():
    from src.services.opinion_retrieval import _pool_anchor_terms
    # Priority order; up to 3 candidates.
    assert _pool_anchor_terms(
        ["consent to search", "terry stop", "miranda rights", "probable cause"]
    ) == ["terry stop", "miranda rights", "probable cause"]
    # Nothing specific -> dense fallbacks only.
    assert _pool_anchor_terms(["coercive", "probable cause"]) == [
        "probable cause"
    ]
    # Nothing fast to query with -> [] (pool skipped, tag path carries).
    assert _pool_anchor_terms(["coercive", "handcuffed"]) == []


# ---------------------------------------------------------------------------
# Legacy path preservation (no analysis_result)
# ---------------------------------------------------------------------------


def test_legacy_tag_overlap_stays_first(fake_db):
    # Without an analysis result, tagged opinions must still outrank
    # untagged text matches even when the latter are far more cited.
    fake_db.tag_rows = [
        _row("Tagged Case", cite_count=10,
             situation_tags=["fourth_amendment"], summary="some text"),
        _row("", cite_count=7, situation_tags=["fourth_amendment"],
             summary="junk header row"),  # junk must drop
    ]
    fake_db.ilike_rows = [
        _row("Famous Search Case", cite_count=150, summary=(
            "fourth amendment search and seizure analysis."
        )),
    ]
    opinions = get_relevant_opinions(["fourth_amendment"], limit=3)
    names = [o["case_name"] for o in opinions]
    assert names[0] == "Tagged Case", names
    assert "" not in names, "junk row leaked through the tag path"


def test_legacy_ilike_still_contributes(fake_db):
    # Tag path short -> ILIKE fills the remainder (legacy trigger intact).
    fake_db.tag_rows = []
    fake_db.ilike_rows = [
        _row("Fourth Amendment Case", cite_count=50, summary=(
            "the fourth amendment protects against unreasonable searches"
        )),
    ]
    opinions = get_relevant_opinions(["fourth_amendment"], limit=3)
    assert [o["case_name"] for o in opinions] == ["Fourth Amendment Case"]
    assert set(opinions[0].keys()) == _OPINION_COLUMNS_KEYS


# ---------------------------------------------------------------------------
# Charge-class gate unchanged — fires before any DB work even when fact
# terms would exist.
# ---------------------------------------------------------------------------


def test_class_only_gate_ignores_fact_terms(monkeypatch):
    monkeypatch.setattr(opinion_retrieval.db, "client", _ExplodingClient())
    monkeypatch.setattr(orin_opinions, "search_orin_opinions", lambda *a, **k: [])
    assert get_relevant_opinions(
        ["misdemeanor"], analysis_result=_herrera_v2(),
    ) == []
    assert get_relevant_opinions(["felony", "dui"]) == []


# ---------------------------------------------------------------------------
# Charge-context exclusion (Joe ruling 2026-08-27)
# ---------------------------------------------------------------------------

_MURDER_ROW = _row(
    "McWatters v. State", cite_count=98,
    summary=(
        "McWatters was convicted of murdering three women; his confession "
        "followed a Miranda waiver he claimed was invalid."
    ),
    situation_tags=["fourth_amendment"],
)
_CONSENT_ROW = _row(
    "Caldwell v. State", cite_count=52,
    summary=(
        "The officer read Caldwell his Miranda rights before questioning him "
        "about a burglary seen on video."
    ),
    situation_tags=["fourth_amendment"],
)


def _herrera_murder_charge() -> dict:
    v2 = _herrera_v2()
    v2["charges_explained"] = [
        {"charge": "Second Degree Murder", "plain_english": "a homicide charge"}
    ]
    return v2


def _herrera_misdemeanor_charge() -> dict:
    v2 = _herrera_v2()
    v2["charges_explained"] = [
        {"charge": "Disorderly Conduct", "plain_english": "a misdemeanor charge"}
    ]
    return v2


def test_homicide_rows_excluded_when_report_has_no_homicide_charge(fake_db):
    fake_db.tag_rows = [_MURDER_ROW, _CONSENT_ROW]
    opinions = get_relevant_opinions(
        ["fourth_amendment"], limit=3, analysis_result=_herrera_v2(),
    )
    names = [o["case_name"] for o in opinions]
    assert "McWatters v. State" not in names, names
    assert "Caldwell v. State" in names, names


def test_homicide_rows_kept_when_report_has_homicide_charge(fake_db):
    fake_db.tag_rows = [_MURDER_ROW, _CONSENT_ROW]
    opinions = get_relevant_opinions(
        ["fourth_amendment"], limit=3,
        analysis_result=_herrera_murder_charge(),
    )
    names = [o["case_name"] for o in opinions]
    assert "McWatters v. State" in names, names


def test_felony_case_kept_for_misdemeanor_only_report(fake_db):
    # Joe's explicit example: Caldwell (a burglary-felony case) STAYS for a
    # misdemeanor-report user — only the homicide rung is hard.
    felony_row = _row(
        "Caldwell v. State", cite_count=52,
        summary=(
            "The officer read Caldwell his Miranda rights before questioning "
            "him about a burglary seen on video."
        ),
        situation_tags=["fourth_amendment"],
    )
    fake_db.tag_rows = [felony_row, _CONSENT_ROW]
    opinions = get_relevant_opinions(
        ["fourth_amendment"], limit=3,
        analysis_result=_herrera_misdemeanor_charge(),
    )
    names = [o["case_name"] for o in opinions]
    assert "Caldwell v. State" in names, names


def test_exclusion_skipped_without_analysis_result(fake_db):
    # Legacy callers pass no analysis_result -> no charge context -> no
    # exclusion (murder rows must still be retrievable via tags alone).
    fake_db.tag_rows = [_MURDER_ROW]
    opinions = get_relevant_opinions(["fourth_amendment"], limit=3)
    assert [o["case_name"] for o in opinions] == ["McWatters v. State"]


def test_report_has_homicide_charge_classification():
    from src.services.opinion_retrieval import _report_has_homicide_charge
    assert _report_has_homicide_charge(_herrera_murder_charge()) is True
    assert _report_has_homicide_charge(_herrera_v2()) is False
    assert _report_has_homicide_charge(_herrera_misdemeanor_charge()) is False
    assert _report_has_homicide_charge(None) is False


def test_row_is_homicide_classification():
    from src.services.opinion_retrieval import _row_is_homicide
    assert _row_is_homicide(_MURDER_ROW) is True
    assert _row_is_homicide(_CONSENT_ROW) is False
    assert _row_is_homicide(_row("X", summary="")) is False


# ---------------------------------------------------------------------------
# Anchor advancement on junk-only / below-threshold results
# (Joe ruling 2026-08-27)
# ---------------------------------------------------------------------------


class _PerFilterQuery:
    """Serves different rows per or_ filter substring (anchor-aware)."""

    def __init__(self, client):
        self._c = client
        self._mode = None
        self._filter = ""

    def select(self, *a, **k):  # noqa: ANN001
        return self

    def overlaps(self, *a, **k):  # noqa: ANN001
        self._mode = "tag"
        return self

    def or_(self, f, *a, **k):  # noqa: ANN001
        self._mode = "ilike"
        self._filter = f
        self._c.captured_filters.append(f)
        return self

    def eq(self, *a, **k):  # noqa: ANN001
        return self

    def order(self, *a, **k):  # noqa: ANN001
        return self

    def limit(self, *a, **k):  # noqa: ANN001
        return self

    def execute(self):  # noqa: ANN201
        if self._mode == "ilike":
            for key, rows in self._c.mapping.items():
                if key in self._filter:
                    return type("_R", (), {"data": list(rows)})()
            return type("_R", (), {"data": []})()
        return type("_R", (), {"data": list(self._c.tag_rows)})()


class _PerFilterClient:
    def __init__(self, mapping, tag_rows=None):
        self.mapping = mapping  # {filter substring: rows}
        self.tag_rows = list(tag_rows or [])
        self.captured_filters = []

    def table(self, *a, **k):  # noqa: ANN001
        return _PerFilterQuery(self)


@pytest.fixture
def per_filter_db(monkeypatch):
    client = _PerFilterClient({})
    monkeypatch.setattr(opinion_retrieval.db, "client", client)
    monkeypatch.setattr(orin_opinions, "search_orin_opinions", lambda *a, **k: [])
    return client


def test_junk_only_anchor_does_not_consume_anchor_budget(per_filter_db):
    # Anchor 1 ('language barrier') returns ONLY empty-case_name junk rows;
    # the loop must advance to anchor 2 ('interpreter') instead of stopping.
    per_filter_db.mapping = {
        "language barrier": [_row("", summary="junk header text")],
        "interpreter": [
            _row("Interpreter Case A", cite_count=10,
                 summary="an interpreter was required under Miranda"),
            _row("Interpreter Case B", cite_count=8,
                 summary="Miranda rights read with an interpreter present"),
        ],
    }
    opinions = get_relevant_opinions(
        ["fourth_amendment"], limit=3, analysis_result=_herrera_v2(),
    )
    names = [o["case_name"] for o in opinions]
    assert "Interpreter Case A" in names, names
    assert "" not in names, "junk row leaked through"
    assert any("language barrier" in f for f in per_filter_db.captured_filters), (
        "anchor 1 was never queried: %r" % per_filter_db.captured_filters
    )
    assert any("interpreter" in f for f in per_filter_db.captured_filters), (
        "anchor 2 was never queried — junk-only anchor consumed the budget: "
        "%r" % per_filter_db.captured_filters
    )


def test_rich_anchor_stops_the_loop(per_filter_db):
    # Anchor 1 returns >= _ANCHOR_MIN_USABLE_ROWS real rows -> the loop must
    # stop there and never query anchor 2.
    per_filter_db.mapping = {
        "language barrier": [
            _row("Barrier Case A", cite_count=9,
                 summary="language barrier and no interpreter for the waiver"),
            _row("Barrier Case B", cite_count=7,
                 summary="Miranda and a documented language barrier"),
        ],
        "interpreter": [
            _row("Interpreter Case C", cite_count=99,
                 summary="interpreter provided for the interrogation"),
        ],
    }
    opinions = get_relevant_opinions(
        ["fourth_amendment"], limit=3, analysis_result=_herrera_v2(),
    )
    names = [o["case_name"] for o in opinions]
    assert "Barrier Case A" in names, names
    assert not any(
        "interpreter" in f for f in per_filter_db.captured_filters
    ), "rich anchor should have consumed the budget; loop ran on"

