"""Unit tests for NotificationService delivery — Phase 6.

Locks in the email-fallback honesty contract: send_email must NOT fake success
when no provider is configured. Faking success would silently advance
reminder_state to 'sent' while no reminder was delivered — the exact failure
mode this product exists to prevent for legal deadlines.

No network: with EMAIL_PROVIDER unset, send_email short-circuits before any
HTTP call, so these are fast and CI-safe.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from src.core.notifications import NotificationService  # noqa: E402
from src.core.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def _no_email_provider(monkeypatch):
    """Run every test with no email provider configured (the shipped default)."""
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "")


def test_send_email_fails_honestly_when_unconfigured():
    """No provider configured -> False, never a fake success."""
    svc = NotificationService()
    ok = asyncio.run(svc.send_email("user@example.com", "subj", "body"))
    assert ok is False


def test_deliver_email_fallback_reports_failure_not_success():
    """No push token + no provider -> (False, 'email'), not (True, 'email').

    This is the web-user path: the result must report failure so the reminder
    is marked 'failed' rather than silently 'sent'.
    """
    svc = NotificationService()
    ok, channel = asyncio.run(svc.deliver(
        expo_token=None, email="user@example.com",
        title="Deadline approaching", body="...",
    ))
    assert ok is False
    assert channel == "email"


def test_deliver_no_contact_returns_none_channel():
    """No token and no email on file -> (False, 'none')."""
    svc = NotificationService()
    ok, channel = asyncio.run(svc.deliver(
        expo_token=None, email=None, title="t", body="b",
    ))
    assert ok is False
    assert channel == "none"


def test_send_push_rejects_non_expo_token_without_network():
    """A value that isn't an Expo token (e.g. a user id passed by mistake)
    is rejected before any HTTP call. Guards against callers that pass the
    wrong identifier as the push token."""
    svc = NotificationService()
    ok = asyncio.run(svc.send_push("not-a-real-token", "t", "b"))
    assert ok is False
