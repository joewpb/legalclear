"""C2 — provider-agnostic email delivery adapter (Decision 8).

Ships DARK: without RESEND_API_KEY configured, get_email_provider() returns
LoggingEmailProvider, which logs and returns False. Callers (notifications.py)
must not treat that False as anything but a real delivery failure — the
reminder pipeline records it as 'failed' until a provider key lands.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email. Returns True only on confirmed delivery."""


class ResendEmailProvider(EmailProvider):
    def __init__(self, api_key: str, from_addr: str):
        self._api_key = api_key
        self._from_addr = from_addr

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        payload = {
            "from": self._from_addr,
            "to": [to],
            "subject": subject,
            "text": body,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(RESEND_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("ResendEmailProvider.send_email failed for to=%r: %s", to, e)
            return False


class LoggingEmailProvider(EmailProvider):
    """Fallback used when no email provider is configured. Never delivers."""

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        logger.warning(
            "LoggingEmailProvider: no email provider configured — not "
            "delivered (to=%r subject=%r)",
            to, subject,
        )
        return False


def get_email_provider() -> EmailProvider:
    """Select the email provider from config. Falls back to logging-only
    when the configured provider has no key (ships dark by default)."""
    provider = (settings.EMAIL_PROVIDER or "").strip().lower()
    if provider == "resend" and settings.RESEND_API_KEY and settings.EMAIL_FROM:
        return ResendEmailProvider(settings.RESEND_API_KEY, settings.EMAIL_FROM)
    return LoggingEmailProvider()
