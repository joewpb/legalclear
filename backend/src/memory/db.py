class DatabaseManager:

    def __init__(self):
        import logging

        from supabase import create_client

        from src.core.config import settings
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
        if self.client is None:
            return {}
        try:
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
        except Exception as e:
            self.logger.error(f"get_or_create_user failed for {email}: {e}")
            return {}

    def update_user_subscription(
            self, user_id: str, status: str,
            subscription_id: str | None = None) -> dict:
        if self.client is None:
            return {}
        try:
            update = {"subscription_status": status}
            if subscription_id:
                update["subscription_id"] = subscription_id
            result = (self.client.table("users")
                      .update(update)
                      .eq("id", user_id).execute())
            return result.data[0] if result.data else {}
        except Exception as e:
            self.logger.error(f"update_user_subscription failed for {user_id}: {e}")
            return {}

    def get_user(self, user_id: str) -> dict:
        if self.client is None:
            return None
        try:
            result = (self.client.table("users")
                      .select("*").eq("id", user_id)
                      .execute())
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"get_user failed for {user_id}: {e}")
            return None

    def mark_free_doc_used(self, user_id: str):
        if self.client is None:
            return
        try:
            self.client.table("users").update(
                {"free_doc_used": True}
            ).eq("id", user_id).execute()
        except Exception as e:
            self.logger.error(f"mark_free_doc_used failed for {user_id}: {e}")

    def save_push_token(
            self, user_id: str,
            expo_token: str,
            platform: str) -> dict:
        if self.client is None:
            return {}
        try:
            result = (self.client.table("push_tokens")
                      .upsert({"user_id": user_id,
                               "expo_token": expo_token,
                               "platform": platform})
                      .execute())
            return result.data[0] if result.data else {}
        except Exception as e:
            self.logger.error(f"save_push_token failed for {user_id}: {e}")
            return {}

    def create_session(
            self, user_id: str, filename: str,
            token_count: int, price_tier: str,
            price_usd: float,
            payment_type: str) -> str:
        if self.client is None:
            return None
        try:
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
        except Exception as e:
            self.logger.error(f"create_session failed for {user_id}: {e}")
            return None

    def update_payment_status(
            self, session_id: str, status: str,
            payment_intent: str | None = None,
            subscription_id: str | None = None):
        if self.client is None:
            return
        try:
            update = {"payment_status": status}
            if payment_intent:
                update["stripe_payment_intent"] = payment_intent
            if subscription_id:
                update["stripe_subscription_id"] = subscription_id
            self.client.table("sessions").update(
                update).eq("id", session_id).execute()
        except Exception as e:
            self.logger.error(f"update_payment_status failed for {session_id}: {e}")

    def get_session(self, session_id: str) -> dict:
        if self.client is None:
            return None
        try:
            result = (self.client.table("sessions")
                      .select("*").eq("id", session_id)
                      .execute())
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"get_session failed for {session_id}: {e}")
            return None

    def create_document(
            self, session_id: str,
            document_text: str = "") -> str:
        if self.client is None:
            return None
        try:
            result = (self.client.table("documents")
                      .insert({
                          "session_id": session_id,
                          "document_text": document_text,
                          "status": "processing"
                      }).execute())
            return result.data[0]["id"]
        except Exception as e:
            self.logger.error(f"create_document failed for session {session_id}: {e}")
            return None

    def save_results(
            self, document_id: str,
            classification: dict,
            explanation: dict,
            form_guide: dict,
            risk_scan: dict,
            expungement_guide: dict,
            escalation: dict,
            language: str):
        if self.client is None:
            return
        try:
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
        except Exception as e:
            self.logger.error(f"save_results failed for {document_id}: {e}")

    def update_document_status(
            self, document_id: str,
            status: str):
        if self.client is None:
            return
        try:
            self.client.table("documents").update(
                {"status": status}
            ).eq("id", document_id).execute()
        except Exception as e:
            self.logger.error(f"update_document_status failed for {document_id}: {e}")

    def get_document(self, document_id: str) -> dict:
        if self.client is None:
            return None
        try:
            result = (self.client.table("documents")
                      .select("*").eq("id", document_id)
                      .execute())
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"get_document failed for {document_id}: {e}")
            return None

    def delete_document(self, document_id: str, session_id: str) -> bool:
        """Delete a document, but only if it belongs to the given session."""
        if self.client is None:
            return False
        try:
            result = (self.client.table("documents")
                      .delete()
                      .eq("id", document_id)
                      .eq("session_id", session_id)
                      .execute())
            return len(result.data) > 0
        except Exception as e:
            self.logger.error(f"delete_document failed for {document_id}: {e}")
            return False

    def get_user_documents(
            self, user_id: str,
            limit: int = 20) -> list:
        if self.client is None:
            return []
        try:
            result = (self.client.table("documents")
                      .select("*, sessions!inner(user_id)")
                      .eq("sessions.user_id", user_id)
                      .order("created_at", desc=True)
                      .limit(limit).execute())
            return result.data if result.data else []
        except Exception as e:
            self.logger.error(f"get_user_documents failed for {user_id}: {e}")
            return []

    def save_message(
            self, document_id: str,
            role: str, content: str,
            language: str = "en") -> str:
        if self.client is None:
            return None
        try:
            result = (self.client.table("chat_messages")
                      .insert({
                          "document_id": document_id,
                          "role": role,
                          "content": content,
                          "language": language
                      }).execute())
            return result.data[0]["id"]
        except Exception as e:
            self.logger.error(f"save_message failed for {document_id}: {e}")
            return None

    def get_history(
            self, document_id: str) -> list:
        if self.client is None:
            return []
        try:
            result = (self.client.table("chat_messages")
                      .select("*")
                      .eq("document_id", document_id)
                      .order("created_at", desc=False)
                      .execute())
            return result.data if result.data else []
        except Exception as e:
            self.logger.error(f"get_history failed for {document_id}: {e}")
            return []

    def count_filings(self, user_id: str) -> int:
        if self.client is None:
            return 0
        try:
            result = (self.client.table("filings")
                      .select("id")
                      .eq("user_id", user_id)
                      .execute())
            return len(result.data) if result.data else 0
        except Exception as e:
            self.logger.error(f"count_filings failed: {e}")
            return 0

    def record_filing(self, user_id: str, document_id: str,
                      filing_type: str = "florida",
                      jurisdiction: str = "FL") -> bool:
        if self.client is None:
            return False
        try:
            self.client.table("filings").insert({
                "user_id": user_id,
                "document_id": document_id,
                "filing_type": filing_type,
                "jurisdiction": jurisdiction
            }).execute()
            return True
        except Exception as e:
            self.logger.error(f"record_filing failed: {e}")
            return False

    def log_usage(
            self, category: str,
            jurisdiction: str, language: str,
            price_tier: str,
            processing_time: float):
        if self.client is None:
            return
        try:
            self.client.table("usage_stats").insert({
                "document_category": category,
                "jurisdiction": jurisdiction,
                "language": language,
                "price_tier": price_tier,
                "processing_time_seconds": processing_time
            }).execute()
        except Exception as e:
            self.logger.error(f"log_usage failed: {e}")

    def redact_document_pii(self, document_id: str) -> dict:
        """Run PII redaction on a document's stored text after extraction.

        Reads the current document_text, runs the PII redactor, and updates
        the row with the redacted version. Returns the redaction audit log
        so callers can verify what was removed.

        Returns:
            dict with keys: redacted (bool), findings_count (int), error (str|None)
        """
        if self.client is None:
            return {"redacted": False, "findings_count": 0, "error": "db_unavailable"}
        try:
            from src.ingestion.pii_redactor import redact_pii

            # Read current text
            result = (self.client.table("documents")
                      .select("document_text")
                      .eq("id", document_id)
                      .execute())
            if not result.data:
                return {"redacted": False, "findings_count": 0, "error": "document_not_found"}

            text = result.data[0].get("document_text")
            if not text:
                return {"redacted": False, "findings_count": 0, "error": None}

            # Run redaction
            redaction = redact_pii(text)
            if redaction["count"] == 0:
                return {"redacted": False, "findings_count": 0, "error": None}

            # Update with redacted text
            self.client.table("documents").update({
                "document_text": redaction["redacted_text"]
            }).eq("id", document_id).execute()

            self.logger.info(
                f"PII redaction complete for {document_id}: "
                f"{redaction['count']} findings"
            )
            return {
                "redacted": True,
                "findings_count": redaction["count"],
                "error": None,
            }
        except Exception as e:
            self.logger.error(f"PII redaction failed for {document_id}: {e}")
            return {"redacted": False, "findings_count": 0, "error": str(e)}
