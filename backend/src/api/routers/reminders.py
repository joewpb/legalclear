"""Phase 6 — Reminder processing endpoint.

Called hourly by pg_cron. For each pending/scheduled deadline:
1. Mark expired if due_date has passed.
2. Create deadline_reminders rows if schedule not yet built.
3. Fire any reminder whose fire_at <= now.
4. Update deadlines.reminder_state.

Guardrail: never send a reminder implying time remains when expired.
"""

import logging
import traceback
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.config import settings
from src.core.notifications import NotificationService
from src.core.reminders import compute_reminder_schedule, get_copy
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reminders", tags=["reminders"])
db = DatabaseManager()
notifier = NotificationService()


def _require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@router.post("/process", dependencies=[Depends(_require_api_key)])
async def process_reminders():
    """Hourly reminder processing loop.

    Returns a summary of what was processed.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(tz=timezone.utc)
    today = now.date()

    stats = {
        "expired": 0,
        "schedules_created": 0,
        "reminders_sent": 0,
        "errors": 0,
    }

    # ── Step 1: mark past deadlines as expired ────────────────────────────────
    try:
        expired = (db.client.table("deadlines")
                   .update({"reminder_state": "expired"})
                   .lt("due_date", today.isoformat())
                   .in_("reminder_state", ["pending", "scheduled"])
                   .execute())
        stats["expired"] = len(expired.data or [])
    except Exception as e:
        logger.error("expire pass failed: %s", e)
        stats["errors"] += 1

    # ── Step 2: load pending/scheduled deadlines with their document context ──
    try:
        rows = (db.client.table("deadlines")
                .select(
                    "id,due_date,severity,reminder_state,"
                    "document_id,"
                    "documents(session_id,"
                    "  sessions(user_id,"
                    "    users(expo_push_token,email,preferred_language)))"
                )
                .in_("reminder_state", ["pending", "scheduled"])
                .gte("due_date", today.isoformat())
                .execute())
        deadlines = rows.data or []
    except Exception as e:
        logger.error("deadline fetch failed: %s", e)
        return stats

    for dl in deadlines:
        dl_id = dl["id"]
        due_date = date.fromisoformat(dl["due_date"])
        severity = dl.get("severity", "medium")

        # Extract user info safely through the join chain
        user_info = _extract_user(dl)
        expo_token = user_info.get("expo_push_token")
        email = user_info.get("email")
        lang = user_info.get("preferred_language", "en") or "en"

        # ── Step 3: create reminder schedule if not yet created ───────────────
        existing = (db.client.table("deadline_reminders")
                    .select("id,fire_at,type,state")
                    .eq("deadline_id", dl_id)
                    .execute())
        existing_rows = existing.data or []

        if not existing_rows:
            schedule = compute_reminder_schedule(due_date, severity, now)
            for spec in schedule:
                try:
                    db.client.table("deadline_reminders").insert({
                        "deadline_id": dl_id,
                        "fire_at": spec.fire_at.isoformat(),
                        "type": spec.type,
                        "state": "scheduled",
                    }).execute()
                    stats["schedules_created"] += 1
                except Exception as e:
                    logger.error("create reminder row failed: %s", e)
                    stats["errors"] += 1
            # Reload
            existing_rows = (db.client.table("deadline_reminders")
                             .select("id,fire_at,type,state")
                             .eq("deadline_id", dl_id)
                             .execute()).data or []
            # Advance reminder_state from pending → scheduled
            if existing_rows:
                db.client.table("deadlines").update(
                    {"reminder_state": "scheduled"}
                ).eq("id", dl_id).execute()

        # ── Step 4: fire due reminders ────────────────────────────────────────
        due_rows = [
            r for r in existing_rows
            if r["state"] == "scheduled"
            and datetime.fromisoformat(r["fire_at"]).replace(tzinfo=timezone.utc) <= now
        ]

        for reminder_row in due_rows:
            rtype = reminder_row["type"]

            # GUARDRAIL: never send "time remains" message on expired deadline
            if due_date < today and rtype != "expired":
                db.client.table("deadline_reminders").update(
                    {"state": "failed"}
                ).eq("id", reminder_row["id"]).execute()
                continue

            copy = get_copy(rtype, lang)
            success, channel = await notifier.deliver(
                expo_token=expo_token,
                email=email,
                title=copy["title"],
                body=copy["body"],
                data={"deadline_id": dl_id, "type": rtype},
            )

            state = "sent" if success else "failed"
            sent_at = now.isoformat() if success else None
            db.client.table("deadline_reminders").update({
                "state": state,
                "sent_at": sent_at,
                "channel": channel,
            }).eq("id", reminder_row["id"]).execute()

            if success:
                stats["reminders_sent"] += 1
            else:
                stats["errors"] += 1

        # Advance reminder_state once every reminder has fired. Mark 'sent'
        # ONLY if every reminder actually delivered; if any failed (e.g. no
        # email provider configured, or no push token/email on file) mark
        # 'failed' so the gap is visible and we never claim a reminder was
        # delivered when it wasn't.
        all_rows = (db.client.table("deadline_reminders")
                    .select("state")
                    .eq("deadline_id", dl_id)
                    .execute()).data or []
        all_done = all(r["state"] in ("sent", "failed") for r in all_rows)
        if all_done and all_rows:
            any_failed = any(r["state"] == "failed" for r in all_rows)
            final_state = "failed" if any_failed else "sent"
            db.client.table("deadlines").update(
                {"reminder_state": final_state}
            ).eq("id", dl_id).execute()

    return stats


def _extract_user(dl: dict) -> dict:
    """Safely extract user info from the nested join result."""
    try:
        docs = dl.get("documents") or {}
        if isinstance(docs, list):
            docs = docs[0] if docs else {}
        sessions = docs.get("sessions") or {}
        if isinstance(sessions, list):
            sessions = sessions[0] if sessions else {}
        users = sessions.get("users") or {}
        if isinstance(users, list):
            users = users[0] if users else {}
        return users
    except Exception:
        logger.warning("_extract_user failed: %s", traceback.format_exc())
        return {}
