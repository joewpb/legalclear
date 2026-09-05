"""Phase E — deterministic miranda_validity_concern flag pins.

The flag is computed from the LLM's own structured findings — deterministic
given the analysis JSON, zero LLM calls. Pins:

  - miranda_noted=True + high/medium 'miranda' defect -> True
  - miranda_noted=True + high/medium 'language_access' defect -> True
  - low-severity defects alone -> False
  - unrelated (e.g. fourth_amendment) defects -> False
  - miranda_noted=False / null -> False
  - no discrepancies -> False
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.police_report_v2 import miranda_validity_concern


def _parsed(miranda_noted=True, discrepancies=None):
    return {
        "miranda_noted": miranda_noted,
        "discrepancies": discrepancies or [],
    }


def _finding(category, severity="high"):
    return {
        "severity": severity,
        "defect_category": category,
        "description": "x",
        "ask_attorney": "q?",
        "page_ref": None,
    }


def test_true_when_high_miranda_defect():
    parsed = _parsed(discrepancies=[_finding("miranda", "high")])
    assert miranda_validity_concern(parsed) is True


def test_true_when_medium_language_access_defect():
    parsed = _parsed(discrepancies=[_finding("language_access", "medium")])
    assert miranda_validity_concern(parsed) is True


def test_false_for_low_defects_only():
    parsed = _parsed(discrepancies=[
        _finding("miranda", "low"),
        _finding("language_access", "low"),
    ])
    assert miranda_validity_concern(parsed) is False


def test_false_for_unrelated_categories():
    parsed = _parsed(discrepancies=[
        _finding("fourth_amendment", "high"),
        _finding("chain_of_custody", "medium"),
    ])
    assert miranda_validity_concern(parsed) is False


def test_false_when_miranda_not_noted():
    parsed = _parsed(miranda_noted=False,
                     discrepancies=[_finding("miranda", "high")])
    assert miranda_validity_concern(parsed) is False


def test_false_when_miranda_null():
    parsed = _parsed(miranda_noted=None,
                     discrepancies=[_finding("miranda", "high")])
    assert miranda_validity_concern(parsed) is False


def test_false_with_no_discrepancies():
    parsed = _parsed()
    assert miranda_validity_concern(parsed) is False


def test_non_dict_discrepancy_entries_ignored():
    parsed = {
        "miranda_noted": True,
        "discrepancies": ["not a dict", None, _finding("miranda", "high")],
    }
    assert miranda_validity_concern(parsed) is True
