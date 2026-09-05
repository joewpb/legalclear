"""Phase C1 — deterministic citation validation pins.

Pins:
  - extraction of every statute citation form, including the SINGULAR
    "Florida Statute N" (handoff open item #7), "section N, Florida
    Statutes", bare "§ N", and subsection suffixes
  - rules-of-court / Rules-Regulating-The-Florida-Bar forms
  - court-only classification (Ch. 90 Evidence Code + rules + bar rules)
  - scrub behavior: court-only citations stripped + scope note; corpus
    NOT FOUND stripped + unverifiable note; corpus FOUND kept + logged
  - charge citations (document facts) are NEVER stripped, even when the
    corpus lacks them
  - subsection suffixes stripped for the lookup only
  - DB-down: analysis returned unchanged, empty log

Pure Python — scripted fake statutes client, no DB, no LLM, no network.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.services import citation_validation
from src.services.citation_validation import (
    _is_court_only,
    _iter_citations,
    validate_analysis_citations,
)


class _FakeStatutesQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def execute(self):
        return type("_R", (), {"data": list(self._rows)})()


class _FakeClient:
    def __init__(self, rows=None):
        self._rows = list(rows or [])

    def table(self, name):
        assert name == "statutes"
        return _FakeStatutesQuery(self._rows)


@pytest.fixture
def fake_db(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(citation_validation.db, "client", client)
    return client


def _iter_cites(text):
    return [info for _s, _e, info in _iter_citations(text)]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_statute_forms_extract():
    text = (
        "Officer cited F.S. § 893.13(6)(a) in the report. "
        "The analysis also mentioned Florida Statute 90.606 and "
        "section 90.606, Florida Statutes, plus a bare § 90.606 and "
        "Fla. Stat. § 83.60(2)."
    )
    cites = _iter_cites(text)
    nums = [c["num"] for c in cites]
    assert "893.13(6)(a)" in nums
    assert nums.count("90.606") >= 3  # singular + trailing + bare forms
    assert "83.60(2)" in nums
    assert all(c["kind"] == "statute" for c in cites)


def test_rule_and_bar_forms_extract():
    text = (
        "Under Fla. R. Crim. P. 3.111 and Florida Rule of Criminal "
        "Procedure 3.111, plus Rule 4-1.5, Rules Regulating The Florida "
        "Bar."
    )
    cites = _iter_cites(text)
    kinds = {c["kind"] for c in cites}
    assert "rule" in kinds
    assert "bar_rule" in kinds
    assert len(cites) == 3


def test_no_citation_no_matches():
    assert _iter_cites("A plain sentence with no citation at all.") == []


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_court_only_classification():
    assert _is_court_only({"kind": "statute", "num": "90.606"})
    assert _is_court_only({"kind": "statute", "num": "90.606(1)"})
    assert not _is_court_only({"kind": "statute", "num": "893.13(6)(a)"})
    assert not _is_court_only({"kind": "statute", "num": "83.60"})
    assert _is_court_only({"kind": "rule", "num": "3.111"})
    assert _is_court_only({"kind": "bar_rule", "num": "4-1.5"})


# ---------------------------------------------------------------------------
# Scrub / keep behavior
# ---------------------------------------------------------------------------


def _analysis(**overrides):
    base = {
        "incident_summary": "A stop occurred.",
        "probable_cause_summary": None,
        "what_happens_next": "Review.",
        "charges_explained": [
            {"charge": "F.S. § 893.13(6)(a)", "plain_english": "possession"},
        ],
        "discrepancies": [
            {
                "severity": "high",
                "defect_category": "language_access",
                "description": "",
                "ask_attorney": "",
                "page_ref": "p.1",
            },
        ],
        "missing_fields": [],
    }
    base.update(overrides)
    return base


def test_court_only_scrubbed_with_scope_note(fake_db):
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "F.S. § 90.606 imposes interpreter obligations at the roadside."
    )
    out, log = validate_analysis_citations(analysis)

    assert "90.606" not in out["discrepancies"][0]["description"]
    statuses = [e["status"] for e in log]
    assert "scrubbed_court_only" in statuses
    assert out["citation_notes"]
    assert any("court proceedings" in n for n in out["citation_notes"])


def test_not_found_scrubbed_with_note(fake_db):
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "Under F.S. § 999.999 the officer erred."
    )
    out, log = validate_analysis_citations(analysis)

    assert "999.999" not in out["discrepancies"][0]["description"]
    not_found = [e for e in log if e["status"] == "not_found"]
    assert len(not_found) == 1
    assert not_found[0]["section"] == "999.999"
    assert any("could not be verified" in n for n in out["citation_notes"])


def test_verified_kept_and_logged(fake_db):
    fake_db._rows = [{
        "chapter": "893",
        "section": "893.13",
        "title": "Controlled substance possession",
    }]
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "The charge under F.S. § 893.13 carries penalties."
    )
    out, log = validate_analysis_citations(analysis)

    assert "F.S. § 893.13" in out["discrepancies"][0]["description"]
    verified = [e for e in log if e["status"] == "verified"]
    assert len(verified) == 1
    assert verified[0]["section"] == "893.13"
    assert verified[0]["title"] == "Controlled substance possession"


def test_log_carries_full_matched_text_not_base(fake_db):
    """The log entry keeps the ORIGINAL matched text (with subsection);
    only the section field carries the lookup base."""
    fake_db._rows = [{
        "chapter": "893",
        "section": "893.13",
        "title": "Controlled substance possession",
    }]
    analysis = _analysis()
    analysis["what_happens_next"] = (
        "Florida Statute 893.13(6)(a) defines the offense."
    )
    _out, log = validate_analysis_citations(analysis)

    verified = [e for e in log if e["status"] == "verified"]
    assert len(verified) == 1
    assert verified[0]["citation"] == "Florida Statute 893.13(6)(a)"
    assert verified[0]["section"] == "893.13"


def test_subsection_suffix_stripped_for_lookup_only(fake_db):
    fake_db._rows = [{
        "chapter": "893",
        "section": "893.13",
        "title": "Controlled substance possession",
    }]
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "See F.S. § 893.13(6)(b) for the exact subsection."
    )
    out, log = validate_analysis_citations(analysis)

    # kept verbatim in the text, verified via the base section
    assert "F.S. § 893.13(6)(b)" in out["discrepancies"][0]["description"]
    assert any(e["status"] == "verified" for e in log)


def test_charge_citations_never_stripped(fake_db):
    # corpus EMPTY — the charge citation would be "not found" if scanned,
    # but it is a document fact and must survive untouched.
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "The charge F.S. § 893.13(6)(a) controls the analysis."
    )
    out, log = validate_analysis_citations(analysis)

    assert out["charges_explained"][0]["charge"] == "F.S. § 893.13(6)(a)"
    assert "F.S. § 893.13(6)(a)" in out["discrepancies"][0]["description"]
    assert any(e["status"] == "from_report" for e in log)
    assert not any(e["status"] == "not_found" for e in log)


def test_db_none_returns_unchanged(monkeypatch):
    monkeypatch.setattr(citation_validation.db, "client", None)
    analysis = _analysis()
    analysis["discrepancies"][0]["description"] = (
        "F.S. § 90.606 imposes interpreter obligations at the roadside."
    )
    out, log = validate_analysis_citations(analysis)

    assert out is analysis           # untouched object
    assert "90.606" in out["discrepancies"][0]["description"]
    assert log == []


def test_missing_fields_scanned(fake_db):
    analysis = _analysis()
    analysis["discrepancies"] = []
    analysis["missing_fields"] = [{
        "severity": "medium",
        "field_name": "interpreter",
        "why_important": "F.S. § 90.606 requires an interpreter.",
        "page_ref": None,
    }]
    out, log = validate_analysis_citations(analysis)

    assert "90.606" not in out["missing_fields"][0]["why_important"]
    assert any(e["status"] == "scrubbed_court_only" for e in log)
