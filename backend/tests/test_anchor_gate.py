"""Regression tests for S2-7: deadline rules must declare their required
date anchor, and the pipeline must never apply a rule to a date kind it did
not ask for (e.g. an ISSUANCE date standing in for SERVICE of process under
Fla. Stat. § 83.60(2)).

Run: cd backend && uv run python -m pytest tests/test_anchor_gate.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from deadline.pipeline import run_deadline_pipeline
from deadline.rules import RULES
from deadline.extract import _sanitize_events


class _FakeTable:
    def __init__(self, name, recorder):
        self._name = name
        self._recorder = recorder

    def select(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def insert(self, row):
        self._recorder.append((self._name, row))
        return self

    def execute(self):
        return MagicMock(data=[{"id": "fake-id"}])


class _FakeClient:
    def __init__(self):
        self.inserted = []

    def table(self, name):
        return _FakeTable(name, self.inserted)


def _run(event):
    fake_client = _FakeClient()
    fake_db = MagicMock(client=fake_client)
    fake_db.get_user_supplied_service_date = MagicMock(return_value=None)
    extraction = {
        "events": [event],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    with patch(
        "deadline.pipeline.extract_trigger_events",
        new=AsyncMock(return_value=extraction),
    ):
        result = asyncio.run(run_deadline_pipeline("doc-1", "text", fake_db))
    return result, fake_client


def _event(event_type, document_type="eviction_complaint"):
    return {
        "event_type": event_type,
        "event_date": "2026-08-14",
        "service_method": "personal",
        "document_type": document_type,
        "circuit": 20,
        "county": "Lee",
        "case_number": None,
        "raw_text_excerpt": "DATED this 14th day of August, 2026.",
        "confidence": 0.95,
    }


def test_issuance_date_never_stands_in_for_service():
    """S2-7 smoke-test bug: a summons issuance date must NOT feed the
    § 83.60(2) 5-business-day answer deadline, which runs from service."""
    result, client = _run(_event("issued"))

    deadline_rows = [r for name, r in client.inserted if name == "deadlines"]
    assert deadline_rows == [], (
        "Deadline computed from an issuance date — § 83.60(2) runs from "
        f"service of process. Wrote: {deadline_rows}"
    )
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True
    assert any("issued" in r for r in result["escalation_reasons"]), (
        result["escalation_reasons"]
    )


def test_unknown_event_type_is_not_a_valid_anchor():
    result, client = _run(_event("unknown"))
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True


def test_service_date_computes_normally():
    """Baseline: a genuine service date satisfies the anchor and computes."""
    result, client = _run(_event("served"))
    assert result["deadlines_written"] == 1
    deadline_rows = [r for name, r in client.inserted if name == "deadlines"]
    assert len(deadline_rows) == 1
    # 5 business days after 2026-08-14 (Fri): Mon-Fri 17-21 → 2026-08-21
    assert deadline_rows[0]["due_date"] == "2026-08-21"


def test_rendition_anchor_gates_notice_of_appeal():
    """9.110(b) runs from rendition; a served/issued date must not anchor it."""
    result, _ = _run(_event("served", document_type="notice_of_appeal"))
    assert result["deadlines_written"] == 0
    assert result["escalation_needed"] is True

    result, _ = _run(_event("rendered", document_type="notice_of_appeal"))
    assert result["deadlines_written"] == 1


def test_every_rule_declares_required_anchors():
    """Every rule must declare which event kinds it can consume (None means
    the rule is date-independent, e.g. the date is printed on the summons)."""
    for key, rule in RULES.items():
        assert "required_anchors" in rule, f"{key} does not declare an anchor"
        anchors = rule["required_anchors"]
        assert anchors is None or (
            isinstance(anchors, tuple) and len(anchors) > 0
        ), f"{key} anchor malformed: {anchors!r}"


def test_sanitize_preserves_valid_event_type_labels():
    """The extractor must pass through date-kind labels the model returns."""
    text = "Hearing set for August 14, 2026."
    data = {
        "events": [{
            "event_type": "hearing",
            "event_date": "2026-08-14",
            "service_method": "unknown",
            "document_type": "unknown",
            "raw_text_excerpt": text,
            "confidence": 0.9,
        }],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    out = _sanitize_events(data, text)
    assert out["events"][0]["event_type"] == "hearing"


def test_sanitize_coerces_unrecognized_event_type_to_unknown():
    """An off-schema label (e.g. 'signature_date') must be coerced to
    'unknown' so it can never satisfy a rule's anchor downstream."""
    text = "DATED this 14th day of August, 2026."
    data = {
        "events": [{
            "event_type": "signature_date",
            "event_date": "2026-08-14",
            "service_method": "unknown",
            "document_type": "eviction_complaint",
            "raw_text_excerpt": text,
            "confidence": 0.9,
        }],
        "escalation_needed": False,
        "escalation_reason": None,
    }
    out = _sanitize_events(data, text)
    assert out["events"][0]["event_type"] == "unknown"
