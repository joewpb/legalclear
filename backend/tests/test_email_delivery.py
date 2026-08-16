"""Unit tests for the C2 email delivery adapter (Decision 8).

Provider selection is config-driven and must ship dark: no RESEND_API_KEY
or EMAIL_FROM configured -> LoggingEmailProvider, which logs and returns
False. No network calls are made in these tests — the HTTP layer is mocked.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.notifications import NotificationService  # noqa: E402
from src.services.email_delivery import (  # noqa: E402
    LoggingEmailProvider,
    ResendEmailProvider,
    get_email_provider,
)


def test_selects_logging_provider_when_key_absent(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "EMAIL_FROM", "")
    provider = get_email_provider()
    assert isinstance(provider, LoggingEmailProvider)


def test_selects_logging_provider_when_provider_unset(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "some-key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "reminders@legalclear.app")
    provider = get_email_provider()
    assert isinstance(provider, LoggingEmailProvider)


def test_selects_resend_provider_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "reminders@legalclear.app")
    provider = get_email_provider()
    assert isinstance(provider, ResendEmailProvider)


def test_logging_provider_returns_false_without_network():
    provider = LoggingEmailProvider()
    ok = asyncio.run(provider.send_email("user@example.com", "subj", "body"))
    assert ok is False


def test_resend_provider_send_success_mocked_http():
    provider = ResendEmailProvider(api_key="re_test_key", from_addr="reminders@legalclear.app")
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = lambda: None
    with patch("src.services.email_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        ok = asyncio.run(provider.send_email("user@example.com", "subj", "body"))
    assert ok is True


def test_resend_provider_send_failure_mocked_http():
    provider = ResendEmailProvider(api_key="re_test_key", from_addr="reminders@legalclear.app")
    with patch("src.services.email_delivery.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("network error"))
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        ok = asyncio.run(provider.send_email("user@example.com", "subj", "body"))
    assert ok is False


def test_notification_service_send_email_uses_adapter_and_records_failure(monkeypatch):
    """Reminder path: with no provider configured, send_email -> False, the
    existing 'terminates failed' semantics stay intact."""
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "EMAIL_FROM", "")
    svc = NotificationService()
    ok = asyncio.run(svc.send_email("user@example.com", "subj", "body"))
    assert ok is False


def test_notification_service_send_email_reports_provider_failure(monkeypatch):
    """Even with a provider configured, a failed send must propagate as
    False so the reminder is recorded 'failed', not silently 'sent'."""
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "reminders@legalclear.app")
    svc = NotificationService()
    with patch(
        "src.core.notifications.get_email_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.send_email = AsyncMock(return_value=False)
        mock_get_provider.return_value = mock_provider
        ok = asyncio.run(svc.send_email("user@example.com", "subj", "body"))
    assert ok is False
