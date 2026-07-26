"""Phase 6 — Reminder schedule logic.

Pure Python — no DB, no network. Takes a due_date and returns
the list of reminder fire-times for that deadline.

Guardrail: never produce a fire_at that implies time remains
when the deadline has already passed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

ReminderType = Literal["14d", "7d", "3d", "1d", "urgent", "expired"]

# Days-before-due_date → reminder type, keyed by severity
_SCHEDULE: dict[str, list[tuple[int, ReminderType]]] = {
    "fatal":  [(14, "14d"), (7, "7d"), (3, "3d"), (1, "1d")],
    "high":   [(7, "7d"),   (3, "3d"), (1, "1d")],
    "medium": [(3, "3d"),   (1, "1d")],
    "low":    [(1, "1d")],
}

URGENT_HOURS = 12   # within this many hours → fire an urgent reminder


@dataclass
class ReminderSpec:
    type: ReminderType
    fire_at: datetime   # UTC


def compute_reminder_schedule(
    due_date: date,
    severity: str,
    now: datetime | None = None,
) -> list[ReminderSpec]:
    """Return the reminder fire-times for a deadline.

    Only includes reminders that haven't passed yet.
    Returns an [expired] spec (no fire_at in future) if due_date is past.
    Returns an [urgent] spec if within URGENT_HOURS hours.
    """
    now = now or datetime.now(tz=UTC)
    due_dt = datetime(due_date.year, due_date.month, due_date.day,
                      17, 0, 0, tzinfo=UTC)   # 5pm UTC on the due date

    specs: list[ReminderSpec] = []

    # Already expired
    if now >= due_dt:
        return []   # caller marks as expired; no future reminders

    hours_remaining = (due_dt - now).total_seconds() / 3600

    # Urgent window
    if hours_remaining <= URGENT_HOURS:
        urgent_fire = now + timedelta(minutes=5)   # fire almost immediately
        specs.append(ReminderSpec(type="urgent", fire_at=urgent_fire))
        return specs

    # Standard schedule — only include reminders not yet passed
    base = _SCHEDULE.get(severity, _SCHEDULE["low"])
    for days_before, rtype in base:
        fire_dt = due_dt - timedelta(days=days_before)
        if fire_dt > now:
            specs.append(ReminderSpec(type=rtype, fire_at=fire_dt))

    return specs


# ── Notification copy ─────────────────────────────────────────────────────────

_COPY: dict[str, dict[str, dict[str, str]]] = {
    "en": {
        "14d": {
            "title": "Deadline in 14 days",
            "body":  "You have a legal deadline coming up in 14 days. Review it now.",
        },
        "7d": {
            "title": "Deadline in 7 days",
            "body":  "You have a legal deadline in 7 days. Don't wait — act now.",
        },
        "3d": {
            "title": "Deadline in 3 days",
            "body":  "Your deadline is in 3 days. This requires urgent attention.",
        },
        "1d": {
            "title": "Deadline TOMORROW",
            "body":  "Your legal deadline is TOMORROW. Act immediately.",
        },
        "urgent": {
            "title": "URGENT: Deadline within hours",
            "body":  "You have a legal deadline within hours. Seek assistance immediately.",
        },
        "expired": {
            "title": "Deadline has passed",
            "body":  "A legal deadline has passed. Seek legal advice immediately.",
        },
    },
    "es": {
        "14d": {
            "title": "Plazo en 14 días",
            "body":  "Tiene un plazo legal en 14 días. Revíselo ahora.",
        },
        "7d": {
            "title": "Plazo en 7 días",
            "body":  "Tiene un plazo legal en 7 días. No espere — actúe ahora.",
        },
        "3d": {
            "title": "Plazo en 3 días",
            "body":  "Su plazo es en 3 días. Esto requiere atención urgente.",
        },
        "1d": {
            "title": "Plazo MAÑANA",
            "body":  "Su plazo legal es MAÑANA. Actúe de inmediato.",
        },
        "urgent": {
            "title": "URGENTE: Plazo en pocas horas",
            "body":  "Tiene un plazo legal en pocas horas. Busque asistencia de inmediato.",
        },
        "expired": {
            "title": "El plazo ha vencido",
            "body":  "Un plazo legal ha vencido. Busque asesoramiento legal de inmediato.",
        },
    },
}


def get_copy(reminder_type: ReminderType, lang: str = "en") -> dict[str, str]:
    lang = lang if lang in _COPY else "en"
    return _COPY[lang].get(reminder_type, _COPY["en"][reminder_type])
