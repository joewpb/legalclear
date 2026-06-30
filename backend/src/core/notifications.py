"""Phase 6 — Notification delivery: Expo push + email fallback.

Expo push API: https://exp.host/--/api/v2/push/send
Email: stub (logs + records); wire to an email provider in a future phase.
"""

import logging
from typing import Any

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class NotificationService:

    async def send_push(
        self,
        expo_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send an Expo push notification. Returns True on success."""
        if not expo_token or not expo_token.startswith("ExponentPushToken["):
            logger.warning("send_push: invalid or missing Expo token %r", expo_token)
            return False
        payload = {
            "to": expo_token,
            "title": title,
            "body": body,
            "sound": "default",
            "data": data or {},
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(EXPO_PUSH_URL, json=payload)
                resp.raise_for_status()
                result = resp.json()
                # Expo returns {"data": [{"status": "ok"} | {"status": "error", ...}]}
                statuses = result.get("data", [{}])
                if statuses and statuses[0].get("status") == "ok":
                    return True
                logger.warning("Expo push returned non-ok: %s", statuses)
                return False
        except Exception as e:
            logger.error("send_push failed for token %r: %s", expo_token[:20], e)
            return False

    async def send_email(
        self,
        email: str,
        subject: str,
        body: str,
    ) -> bool:
        """Email fallback. Returns True ONLY when a provider actually delivers.

        Until a provider is wired this returns False — it does NOT fake
        success — so the reminder pipeline records the reminder as 'failed'
        instead of silently advancing reminder_state to 'sent'. Web users
        (no Expo push token) rely on this channel, so faking success here
        would mean a legal-deadline reminder that never reaches the user.

        To enable delivery:
          1. Set EMAIL_PROVIDER (e.g. "resend") + its API key in env.
          2. Add the provider SDK to backend deps.
          3. Implement the matching branch below to return True on confirmed
             delivery. Until then a configured-but-unimplemented provider
             also fails honestly (logged at ERROR).
        """
        provider = (settings.EMAIL_PROVIDER or "").strip().lower()
        if not provider:
            logger.warning(
                "send_email: EMAIL_PROVIDER not configured — reminder NOT "
                "delivered (to=%r subject=%r). Set EMAIL_PROVIDER + key to "
                "enable email delivery.",
                email, subject,
            )
            return False
        # TODO(email): dispatch on provider ("resend"/"sendgrid") and return
        # True only on confirmed delivery. Fail honestly until implemented.
        logger.error(
            "send_email: EMAIL_PROVIDER=%r set but send path not implemented "
            "— reminder NOT delivered to=%r",
            provider, email,
        )
        return False

    async def deliver(
        self,
        expo_token: str | None,
        email: str | None,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Try push; fall back to email. Returns (success, channel_used)."""
        if expo_token:
            ok = await self.send_push(expo_token, title, body, data)
            if ok:
                return True, "push"
        if email:
            ok = await self.send_email(email, title, body)
            return ok, "email"
        logger.warning("deliver: no push token or email — notification dropped")
        return False, "none"
