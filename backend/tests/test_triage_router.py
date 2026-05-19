"""Unit tests for the triage routing logic — Phase 5.

Pure Python — no LLM calls, no DB calls.

Run: cd backend && uv run python -m pytest tests/test_triage_router.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from triage.router import route, CONFIDENCE_THRESHOLD


def _cls(doc_type, confidence=0.95, is_criminal=False, is_expungement=False,
         requires_review=False, review_reason=None):
    return {
        "document_type": doc_type,
        "document_type_confidence": confidence,
        "is_criminal": is_criminal,
        "is_expungement": is_expungement,
        "requires_human_review": requires_review,
        "review_reason": review_reason,
    }


# ── Criminal / expungement always escalate ───────────────────────────────────

def test_criminal_escalates():
    r = route(_cls("criminal"))
    assert r["escalate"] is True
    assert r["deadline_rule_keys"] == []
    assert r["safe_to_auto_compute"] is False


def test_expungement_escalates():
    r = route(_cls("expungement"))
    assert r["escalate"] is True
    assert r["safe_to_auto_compute"] is False


def test_is_criminal_flag_escalates_regardless_of_type():
    """is_criminal=True should escalate even if document_type is 'order'."""
    r = route(_cls("order", is_criminal=True))
    assert r["escalate"] is True


def test_is_expungement_flag_escalates():
    r = route(_cls("civil_summons", is_expungement=True))
    assert r["escalate"] is True


# ── Low confidence → human review, no auto-compute ───────────────────────────

def test_low_confidence_requires_review():
    r = route(_cls("civil_summons", confidence=0.50))
    assert r["requires_human_review"] is True
    assert r["safe_to_auto_compute"] is False
    assert r["escalate"] is False


def test_exactly_at_threshold_is_allowed():
    r = route(_cls("civil_summons", confidence=CONFIDENCE_THRESHOLD))
    assert r["requires_human_review"] is False
    assert r["safe_to_auto_compute"] is True


def test_unknown_type_requires_review():
    r = route(_cls("unknown", confidence=0.95))
    assert r["requires_human_review"] is True
    assert r["safe_to_auto_compute"] is False


def test_requires_human_review_flag_propagates():
    r = route(_cls("civil_summons", confidence=0.95, requires_review=True,
                   review_reason="ambiguous formatting"))
    assert r["requires_human_review"] is True
    assert r["safe_to_auto_compute"] is False


# ── Confident classifications → correct rule routing ─────────────────────────

def test_civil_summons_routes_correctly():
    r = route(_cls("civil_summons"))
    assert "civil_summons" in r["deadline_rule_keys"]
    assert r["safe_to_auto_compute"] is True
    assert r["escalate"] is False


def test_eviction_routes_correctly():
    r = route(_cls("eviction_complaint"))
    assert "eviction_complaint" in r["deadline_rule_keys"]
    assert r["safe_to_auto_compute"] is True


def test_family_law_routes_correctly():
    r = route(_cls("family_law_petition"))
    assert "family_law_petition" in r["deadline_rule_keys"]
    assert "divorce" in r["suggested_form_tags"]


def test_judgment_routes_to_appeal_and_rehearing():
    r = route(_cls("judgment"))
    assert "notice_of_appeal" in r["deadline_rule_keys"]
    assert "motion_for_rehearing" in r["deadline_rule_keys"]


def test_discovery_request_routes_correctly():
    r = route(_cls("discovery_request"))
    assert "discovery_request" in r["deadline_rule_keys"]


def test_order_has_no_auto_deadline_rules():
    r = route(_cls("order"))
    assert r["deadline_rule_keys"] == []
    # order may still be surfaced but no auto-compute
    assert r["safe_to_auto_compute"] is False


# ── Escalation takes precedence over confidence ───────────────────────────────

def test_criminal_low_confidence_still_escalates():
    """Criminal escalation must fire even if confidence is low."""
    r = route(_cls("criminal", confidence=0.30))
    assert r["escalate"] is True


def test_escalation_clears_review_flag():
    """Escalated documents should not also show the review dropdown."""
    r = route(_cls("criminal"))
    assert r["requires_human_review"] is False
