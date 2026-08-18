"""G1-1 — anchor_date / anchor_provenance derivation for deadline rows.

Pure Python: tests the _anchor_for_deadline helper directly, no DB, no LLM.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.routers import deadline as deadline_router

TRACE = [{"step": 1, "action": "Trigger event date: 2026-08-10",
          "date": "2026-08-10", "rule": "Fla. Stat. § 83.60(2)"}]


def _a(rule, fact):
    return deadline_router._anchor_for_deadline(rule, TRACE, fact)


def test_no_service_fact_is_extracted():
    date_, prov, note = _a("Fla. Stat. § 83.60(2)", None)
    assert date_ == "2026-08-10"
    assert prov == "extracted"
    assert note is None


def test_user_supplied_service_date_is_user_supplied():
    fact = {"service_date": "2026-08-10", "service_method": "personal"}
    date_, prov, note = _a("Fla. Stat. § 83.60(2)", fact)
    assert date_ == "2026-08-10"
    assert prov == "user_supplied"
    assert note is None


def test_rule_without_served_anchor_stays_extracted():
    # date_of_loss rules: a user-supplied service date never feeds them
    fact = {"service_date": "2026-08-10", "service_method": "personal"}
    date_, prov, note = _a("Fla. Stat. § 95.11(3)(a)", fact)
    assert prov == "extracted"


def test_posted_service_later_of_note():
    fact = {"service_date": "2026-08-10", "service_method": "posted",
            "clerk_mailing_date": "2026-08-12"}
    date_, prov, note = _a("Fla. Stat. § 83.60(2)", fact)
    assert prov == "user_supplied"
    assert note and "later of" in note and "08-12" in note


def test_posted_same_day_no_note():
    fact = {"service_date": "2026-08-10", "service_method": "posted",
            "clerk_mailing_date": "2026-08-10"}
    date_, prov, note = _a("Fla. Stat. § 83.60(2)", fact)
    assert prov == "user_supplied"
    assert note is None
