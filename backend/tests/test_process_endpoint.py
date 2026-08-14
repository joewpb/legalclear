"""Regression test for S2-5b: /process called explain()/scan() with a stale
4-arg signature (doc, classification, lang) after ExplainerAgent.explain()
was tightened to (text, language). This must call the current signatures.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

from fastapi import BackgroundTasks

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api import routes  # noqa: E402


class _FakeTableQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        return MagicMock(data=self._data)


def test_process_document_calls_explain_and_scan_with_text_and_lang(monkeypatch):
    document_text = "This is the raw document text."

    fake_db = MagicMock()
    fake_db.get_session.return_value = {"id": "sess-1", "user_id": None, "price_tier": "small"}
    fake_db.get_user.return_value = None
    fake_db.client = MagicMock()
    fake_db.client.table.return_value = _FakeTableQuery(
        [{"id": "doc-1", "document_text": document_text}]
    )
    fake_db.save_results = MagicMock()
    fake_db.redact_document_pii.return_value = {}
    fake_db.log_usage = MagicMock()
    monkeypatch.setattr(routes, "db", fake_db)

    monkeypatch.setattr(
        routes.classifier,
        "classify",
        AsyncMock(return_value={"document_category": "other", "jurisdiction_name": "FL"}),
    )
    explain_mock = AsyncMock(return_value={"summary": "ok"})
    scan_mock = AsyncMock(return_value={"risks": []})
    monkeypatch.setattr(routes.explainer, "explain", explain_mock)
    monkeypatch.setattr(routes.risk_scanner, "scan", scan_mock)
    monkeypatch.setattr(routes.escalation_router, "route", MagicMock(return_value={}))

    result = asyncio.run(routes.process_document(
        session_id="sess-1",
        background_tasks=BackgroundTasks(),
        lang="en",
    ))

    assert result["explanation"] == {"summary": "ok"}
    explain_mock.assert_awaited_once_with(document_text, "en")
    scan_mock.assert_awaited_once()
