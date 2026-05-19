"""Phase 6 — Notification delivery: Expo push + email fallback.

Expo push API: https://exp.host/--/api/v2/push/send
Email: stub (logs + records); wire to an email provider in a future phase.
"""

import logging
from typing import Any

import httpx

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
        """Email fallback — stub until an email provider is configured.

        Logs the notification so it's auditable. Wire to SES/SendGrid in a
        future phase by replacing this method body.
        """
        logger.info(
            "EMAIL (stub) to=%r subject=%r | Configure an email provider "
            "to deliver this: %s",
            email, subject, body
        )
        return True   # stub always succeeds so reminder_state advances

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
