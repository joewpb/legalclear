"""Unit tests for UPL escalation triggers and disclaimer layer — Phase 8.

Pure Python — no LLM, no DB calls.

Run: cd backend && uv run python -m pytest tests/test_upl.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta, timezone

from src.core.upl import (
    FATAL_CONFIDENCE_THRESHOLD,
    URGENT_HOURS,
    apply_disclaimer,
    audit_output_for_upl,
    check_escalation,
    get_disclaimer,
)

UTC = timezone.utc
NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

def _deadline(severity="fatal", confidence=0.95, due_days_from_now=20,
              label="Answer to Civil Summons"):
    due = (NOW + timedelta(days=due_days_from_now)).date().isoformat()
    return {"severity": severity, "confidence": confidence,
            "due_date": due, "label": label}

def _cls(doc_type="civil_summons", is_criminal=False, is_expungement=False,
         notes=""):
    return {"document_type": doc_type, "is_criminal": is_criminal,
            "is_expungement": is_expungement, "notes": notes}


# ── Trigger 1: fatal + low confidence ────────────────────────────────────────

def test_fatal_low_confidence_escalates():
    dl = _deadline(severity="fatal", confidence=0.85)
    r = check_escalation(_cls(), [dl], now=NOW)
    assert r.should_escalate is True
    assert any("confidence" in reason.lower() for reason in r.reasons)


def test_fatal_at_threshold_does_not_escalate():
    dl = _deadline(severity="fatal", confidence=FATAL_CONFIDENCE_THRESHOLD)
    r = check_escalation(_cls(), [dl], now=NOW)
    # Confidence at threshold = 0.90 is NOT below threshold
    assert not any("confidence" in reason.lower() for reason in r.reasons)


def test_high_severity_low_confidence_does_not_trigger():
    """Trigger 1 only applies to fatal severity."""
    dl = _deadline(severity="high", confidence=0.50)
    r = check_escalation(_cls(), [dl], now=NOW)
    assert not any("confidence" in reason.lower() for reason in r.reasons)


# ── Trigger 2: within 72 hours ────────────────────────────────────────────────

def test_deadline_within_72h_escalates():
    dl = _deadline(due_days_from_now=2)   # 2 days = 48h < 72h
    r = check_escalation(_cls(), [dl], now=NOW)
    assert r.should_escalate is True
    assert r.urgency == "immediate"
    assert any("hours" in reason.lower() for reason in r.reasons)


def test_deadline_just_under_72h_escalates():
    # due_dt = NOW + 2 days at 17:00 = 53h out — safely within 72h window
    dl = _deadline(due_days_from_now=2)
    r = check_escalation(_cls(), [dl], now=NOW)
    assert r.should_escalate is True


def test_deadline_73h_does_not_trigger():
    dl = _deadline(due_days_from_now=4)   # > 72h
    r = check_escalation(_cls(), [dl], now=NOW)
    assert not any("hours" in reason.lower() for reason in r.reasons)


def test_past_deadline_does_not_trigger_72h():
    """An already-expired deadline should not trigger the 72-hour urgent window."""
    dl = _deadline(due_days_from_now=-1)  # yesterday
    r = check_escalation(_cls(), [dl], now=NOW)
    assert not any("hours" in reason.lower() for reason in r.reasons)


# ── Trigger 3: unknown document type ─────────────────────────────────────────

def test_unknown_type_escalates():
    r = check_escalation(_cls("unknown"), [], now=NOW)
    assert r.should_escalate is True
    assert any("type" in reason.lower() or "document" in reason.lower()
               for reason in r.reasons)


def test_none_type_escalates():
    r = check_escalation({"document_type": None}, [], now=NOW)
    assert r.should_escalate is True


def test_known_type_does_not_trigger_3():
    r = check_escalation(_cls("civil_summons"), [], now=NOW)
    assert not any("type" in reason.lower() and "could not" in reason.lower()
                   for reason in r.reasons)


# ── Trigger 4: minor children ─────────────────────────────────────────────────

def test_family_law_petition_escalates_children():
    """Family law petitions always flag for minor-children review."""
    r = check_escalation(_cls("family_law_petition"), [], now=NOW)
    assert r.should_escalate is True
    assert any("child" in reason.lower() for reason in r.reasons)


def test_notes_mention_children_escalates():
    r = check_escalation(_cls("civil_summons", notes="involves minor children"), [], now=NOW)
    assert r.should_escalate is True


# ── Trigger 5: criminal / expungement ────────────────────────────────────────

def test_criminal_type_escalates():
    r = check_escalation(_cls("criminal", is_criminal=True), [], now=NOW)
    assert r.should_escalate is True
    assert r.disclaimer_level == "criminal"
    assert r.urgency == "immediate"


def test_expungement_escalates():
    r = check_escalation(_cls("expungement", is_expungement=True), [], now=NOW)
    assert r.should_escalate is True
    assert r.disclaimer_level == "criminal"


def test_is_criminal_flag_escalates_any_doc_type():
    """is_criminal=True must escalate even if doc_type is 'order'."""
    r = check_escalation(_cls("order", is_criminal=True), [], now=NOW)
    assert r.should_escalate is True


# ── No escalation when all clear ─────────────────────────────────────────────

def test_clean_document_does_not_escalate():
    dl = _deadline(severity="fatal", confidence=0.95, due_days_from_now=20)
    r = check_escalation(_cls("civil_summons"), [dl], now=NOW)
    assert r.should_escalate is False
    assert r.reasons == []


# ── Disclaimer layer ──────────────────────────────────────────────────────────

def test_standard_disclaimer_present():
    d = get_disclaimer("standard", "en")
    assert "legal information" in d.lower()
    assert "not legal advice" in d.lower()


def test_spanish_disclaimer_present():
    d = get_disclaimer("standard", "es")
    assert "información legal" in d.lower()
    assert "asesoramiento legal" in d.lower()


def test_urgent_disclaimer_present():
    d = get_disclaimer("urgent", "en")
    assert "immediately" in d.lower() or "deadline" in d.lower()


def test_apply_disclaimer_adds_field():
    out = apply_disclaimer({"summary": "test"}, "en", "standard")
    assert "disclaimer" in out
    assert "summary" in out   # original fields preserved
    assert "legal information" in out["disclaimer"].lower()


def test_apply_disclaimer_does_not_overwrite_existing():
    """apply_disclaimer should NOT clobber existing keys other than disclaimer."""
    out = apply_disclaimer({"foo": "bar", "disclaimer": "old"}, "en")
    assert out["foo"] == "bar"
    assert "legal information" in out["disclaimer"].lower()


def test_unknown_lang_falls_back_to_english():
    d = get_disclaimer("standard", "zh")
    d_en = get_disclaimer("standard", "en")
    assert d == d_en


# ── UPL audit ─────────────────────────────────────────────────────────────────

def test_audit_catches_you_should():
    flags = audit_output_for_upl("You should file an answer immediately.")
    assert "you should" in flags


def test_audit_clean_text_returns_empty():
    clean = (
        "This document is a civil summons. "
        "The deadline is 20 days after service. "
        "Failure to respond may result in a default judgment."
    )
    flags = audit_output_for_upl(clean)
    assert flags == []


def test_audit_catches_i_recommend():
    flags = audit_output_for_upl("Based on the document, I recommend hiring a lawyer.")
    assert "i recommend" in flags
