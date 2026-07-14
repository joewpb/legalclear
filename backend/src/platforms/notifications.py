import logging

import aiohttp

logger = logging.getLogger(__name__)


class NotificationService:

    async def send(self, user_id: str, title: str,
                   message: str,
                   data: dict = None) -> dict:
        # MESSAGING SLOT
        # Set MESSAGING_PLATFORM in .env to activate.
        # To add WhatsApp: implement send_whatsapp()
        # To add Slack: implement send_slack()
        # To add Discord: implement send_discord()
        logger.info(
            "Notification: user=%s title=%s message=%s",
            user_id, title, message,
        )
        return {"sent": True, "method": "log",
                "message": message}

    async def send_push(self, expo_token: str,
                        title: str, body: str,
                        data: dict = None) -> dict:
        if not expo_token:
            return {"sent": False, "reason": "no_token"}
        payload = {"to": expo_token, "title": title,
                   "body": body, "data": data or {}}
        try:
            async with aiohttp.ClientSession() as s, s.post(
                    "https://exp.host/--/api/v2/push/send",
                    json=payload,
                    headers={"Content-Type":
                             "application/json"}
                ) as resp:
                    ticket = await resp.json()
                    return {"sent": True, "ticket": ticket}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    async def notify_document_ready(
            self, user_id: str, document_id: str,
            lang: str = "en") -> dict:
        title = ("Analisis listo" if lang == "es"
                 else "Analysis ready")
        msg = ("Su documento ha sido analizado."
               if lang == "es"
               else "Your document analysis is ready.")
        return await self.send(
            user_id, title, msg,
            {"document_id": document_id})

    async def notify_payment_confirmed(
            self, user_id: str,
            lang: str = "en") -> dict:
        title = ("Pago confirmado" if lang == "es"
                 else "Payment confirmed")
        msg = ("Su pago fue procesado."
               if lang == "es"
               else "Your payment was processed.")
        return await self.send(user_id, title, msg)
