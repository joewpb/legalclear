class DatabaseManager:

    def __init__(self):
        from supabase import create_client
        from src.core.config import settings
        import logging
        self.logger = logging.getLogger(__name__)
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            self.client = None
            self.logger.warning("Supabase not configured — running in degraded mode")
            return
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY,
            )
        except Exception as e:
            self.logger.error(f"Supabase init failed: {e}")
            self.client = None

    def get_or_create_user(
            self, email: str,
            preferred_language: str = "en") -> dict:
        result = (self.client.table("users")
                  .select("*").eq("email", email)
                  .execute())
        if result.data:
            return result.data[0]
        new_user = (self.client.table("users")
                    .insert({"email": email,
                             "preferred_language":
                             preferred_language})
                    .execute())
        return new_user.data[0]

    def update_user_subscription(
            self, user_id: str, status: str,
            subscription_id: str = None) -> dict:
        update = {"subscription_status": status}
        if subscription_id:
            update["subscription_id"] = subscription_id
        result = (self.client.table("users")
                  .update(update)
                  .eq("id", user_id).execute())
        return result.data[0] if result.data else {}

    def get_user(self, user_id: str) -> dict:
        result = (self.client.table("users")
                  .select("*").eq("id", user_id)
                  .execute())
        return result.data[0] if result.data else {}

    def mark_free_doc_used(self, user_id: str):
        self.client.table("users").update(
            {"free_doc_used": True}
        ).eq("id", user_id).execute()

    def save_push_token(
            self, user_id: str,
            expo_token: str,
            platform: str) -> dict:
        result = (self.client.table("push_tokens")
                  .upsert({"user_id": user_id,
                           "expo_token": expo_token,
                           "platform": platform})
                  .execute())
        return result.data[0] if result.data else {}

    def create_session(
            self, user_id: str, filename: str,
            token_count: int, price_tier: str,
            price_usd: float,
            payment_type: str) -> str:
        result = (self.client.table("sessions")
                  .insert({
                      "user_id": user_id,
                      "document_filename": filename,
                      "document_token_count": token_count,
                      "price_tier": price_tier,
                      "price_paid_usd": price_usd,
                      "payment_type": payment_type
                  }).execute())
        return result.data[0]["id"]

    def update_payment_status(
            self, session_id: str, status: str,
            payment_intent: str = None,
            subscription_id: str = None):
        update = {"payment_status": status}
        if payment_intent:
            update["stripe_payment_intent"] = (
                payment_intent)
        if subscription_id:
            update["stripe_subscription_id"] = (
                subscription_id)
        self.client.table("sessions").update(
            update).eq("id", session_id).execute()

    def get_session(self, session_id: str) -> dict:
        result = (self.client.table("sessions")
                  .select("*").eq("id", session_id)
                  .execute())
        return result.data[0] if result.data else {}

    def create_document(
            self, session_id: str,
            document_text: str = "") -> str:
        result = (self.client.table("documents")
                  .insert({
                      "session_id": session_id,
                      "document_text": document_text,
                      "status": "processing"
                  }).execute())
        return result.data[0]["id"]

    def save_results(
            self, document_id: str,
            classification: dict,
            explanation: dict,
            form_guide: dict,
            risk_scan: dict,
            expungement_guide: dict,
            escalation: dict,
            language: str):
        self.client.table("documents").update({
            "classification": classification,
            "explanation": explanation,
            "form_guide": form_guide,
            "risk_scan": risk_scan,
            "expungement_guide": expungement_guide,
            "escalation": escalation,
            "language": language,
            "status": "complete"
        }).eq("id", document_id).execute()

    def update_document_status(
            self, document_id: str,
            status: str):
        self.client.table("documents").update(
            {"status": status}
        ).eq("id", document_id).execute()

    def get_document(self, document_id: str) -> dict:
        result = (self.client.table("documents")
                  .select("*").eq("id", document_id)
                  .execute())
        return result.data[0] if result.data else {}

    def get_user_documents(
            self, user_id: str,
            limit: int = 20) -> list:
        result = (self.client.table("documents")
                  .select("*, sessions!inner(user_id)")
                  .eq("sessions.user_id", user_id)
                  .order("created_at", desc=True)
                  .limit(limit).execute())
        return result.data if result.data else []

    def save_message(
            self, document_id: str,
            role: str, content: str,
            language: str = "en") -> str:
        result = (self.client.table("chat_messages")
                  .insert({
                      "document_id": document_id,
                      "role": role,
                      "content": content,
                      "language": language
                  }).execute())
        return result.data[0]["id"]

    def get_history(
            self, document_id: str) -> list:
        result = (self.client.table("chat_messages")
                  .select("*")
                  .eq("document_id", document_id)
                  .order("created_at", desc=False)
                  .execute())
        return result.data if result.data else []

    def log_usage(
            self, category: str,
            jurisdiction: str, language: str,
            price_tier: str,
            processing_time: float):
        self.client.table("usage_stats").insert({
            "document_category": category,
            "jurisdiction": jurisdiction,
            "language": language,
            "price_tier": price_tier,
            "processing_time_seconds": processing_time
        }).execute()
