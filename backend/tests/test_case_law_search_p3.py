"""Unit tests for the deterministic case-law search pipeline (Phase 3).

Pure-function coverage: tokenization, name-query detection, ranking,
junk filtering, citation display, response mapping. No DB, no network.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.routers.case_law import (
    _display_citation,
    _has_case_name,
    _has_usable_summary,
    _is_name_query,
    _rank,
    _row_to_result,
    _scrub,
    _tokenize,
)


class TestTokenize:
    def test_space_joined_chip_becomes_keywords(self):
        terms = _tokenize("stand your ground self defense")
        assert "stand" in terms
        assert "ground" in terms
        assert "self" in terms
        assert "defense" in terms
        assert "your" not in terms  # stopword

    def test_hyphen_form_splits(self):
        terms = _tokenize("self-defense")
        assert "self" in terms and "defense" in terms

    def test_stopwords_dropped(self):
        terms = _tokenize("the and of to in on with")
        assert terms == []

    def test_punctuation_and_case_normalized(self):
        terms = _tokenize("Probable, Cause: (Miranda)")
        assert terms == ["probable", "cause", "miranda"]

    def test_short_terms_dropped(self):
        terms = _tokenize("a b c d x 776.012")
        assert terms == ["776", "012"]

    def test_wildcards_scrubbed(self):
        terms = _tokenize("stand%your_ground")
        assert "%" not in "".join(terms)
        assert "stand" in terms

    def test_curly_chars_normalized(self):
        terms = _tokenize("stand\u2019your ground")  # curly apostrophe
        assert "stand" in terms and "ground" in terms

    def test_term_cap(self):
        terms = _tokenize(" ".join(f"word{i}" for i in range(20)))
        assert len(terms) == 8


class TestNameDetection:
    def test_v_dot_detected(self):
        assert _is_name_query("Bush v. Gore")

    def test_vs_detected(self):
        assert _is_name_query("Dennis vs. State")

    def test_v_no_period_detected(self):
        assert _is_name_query("Terry v Ohio")

    def test_plain_query_not_name(self):
        assert not _is_name_query("stand your ground self defense")

    def test_word_with_v_dot_not_name(self):
        assert not _is_name_query("probable cause")


class TestJunkFilter:
    def test_empty_name_rejected(self):
        assert not _has_case_name({"case_name": ""})
        assert not _has_case_name({"case_name": None})
        assert not _has_case_name({})

    def test_real_name_accepted(self):
        assert _has_case_name({"case_name": "Dennis v. State"})

    def test_tiny_summary_rejected(self):
        assert not _has_usable_summary({"summary_plain": "NOT FINAL UNTIL"})

    def test_missing_summary_rejected(self):
        assert not _has_usable_summary({"summary_plain": None})

    def test_real_summary_accepted(self):
        assert _has_usable_summary({"summary_plain": "x" * 150})


class TestRanking:
    def test_matched_terms_first(self):
        rows = [
            {"case_name": "A", "summary_plain": "murder murder", "cite_count": 1, "cluster_id": 1},
            {"case_name": "B", "summary_plain": "murder battery", "cite_count": 1, "cluster_id": 2},
            {"case_name": "C", "summary_plain": "murder battery theft", "cite_count": 0, "cluster_id": 3},
        ]
        ranked = _rank(rows, ["murder", "battery", "theft"])
        assert [r["case_name"] for r in ranked] == ["C", "B", "A"]

    def test_cite_count_tiebreak(self):
        rows = [
            {"case_name": "A", "summary_plain": "murder", "cite_count": 5, "cluster_id": 1},
            {"case_name": "B", "summary_plain": "murder", "cite_count": 9, "cluster_id": 2},
        ]
        ranked = _rank(rows, ["murder"])
        assert [r["case_name"] for r in ranked] == ["B", "A"]

    def test_cluster_id_stable_tiebreak(self):
        rows = [
            {"case_name": "A", "summary_plain": "murder", "cite_count": 5, "cluster_id": 1},
            {"case_name": "B", "summary_plain": "murder", "cite_count": 5, "cluster_id": 2},
        ]
        ranked = _rank(rows, ["murder"])
        assert [r["case_name"] for r in ranked] == ["B", "A"]
        again = _rank(rows, ["murder"])
        assert [r["case_name"] for r in again] == ["B", "A"]  # deterministic

    def test_zero_matches_dropped(self):
        rows = [
            {"case_name": "A", "summary_plain": "nothing here", "cite_count": 99, "cluster_id": 1},
        ]
        assert _rank(rows, ["murder"]) == []

    def test_case_name_counts_toward_match(self):
        rows = [
            {"case_name": "Bush v. Gore", "summary_plain": "x" * 150, "cite_count": 0, "cluster_id": 1},
        ]
        assert _rank(rows, ["bush"]) != []


class TestDisplayCitation:
    def test_empty_becomes_not_available(self):
        assert _display_citation({"citation": ""}) == "Not available"
        assert _display_citation({"citation": None}) == "Not available"
        assert _display_citation({}) == "Not available"

    def test_placeholders_rejected(self):
        for bad in ("N/A", "n/a", "null", "unknown", "tbd", "pending", "Not cited"):
            assert _display_citation({"citation": bad}) == "Not available"

    def test_real_citation_preserved(self):
        assert _display_citation({"citation": "51 So. 3d 687"}) == "51 So. 3d 687"


class TestRowMapping:
    def test_null_treatment_stays_null_not_string(self):
        row = {
            "case_name": "A v. B", "citation": "1 So. 2d 2", "court": "C",
            "date_filed": "2010-01-01", "cite_count": 3, "summary_plain": "s" * 150,
            "cluster_id": 42, "_treatment": None,
        }
        out = _row_to_result(row)
        assert out["citation_treatment"] is None  # never the string "None"

    def test_treatment_passed_through(self):
        row = {
            "case_name": "A v. B", "citation": "", "court": "C",
            "date_filed": "", "cite_count": 0, "summary_plain": None,
            "cluster_id": None, "_treatment": [{"type": "reversed", "text": "t"}],
        }
        out = _row_to_result(row)
        assert out["citation_treatment"] == [{"type": "reversed", "text": "t"}]
        assert out["citation"] == "Not available"

    def test_url_from_cluster_id(self):
        out = _row_to_result({"case_name": "A", "cluster_id": 4314145})
        assert out["courtlistener_url"] == "https://www.courtlistener.com/opinion/4314145/"

    def test_url_null_without_cluster(self):
        out = _row_to_result({"case_name": "A"})
        assert out["courtlistener_url"] is None

    def test_control_chars_scrubbed(self):
        out = _row_to_result({"case_name": "A", "summary_plain": "bad\ffeed"})
        assert "\f" not in out["plain_english_summary"]

    def test_scrub_none_safe(self):
        assert _scrub(None) is None
