"""I-4 — deterministic claim state machine (Phase I finale, 2026-08-23).

No LLM. No legal deadline arithmetic (that stays in deadline/compute.py —
this module only classifies phase status from observed trigger events and
computes UI progress metadata from event timestamps).

Disclaimer contract: this module emits no standalone user-facing prose —
its output is wrapped by the canonical ``apply_disclaimer``
(src/core/upl.py) at the claims router boundary.

Data-driven: phase topology (entry/exit triggers, typical windows, sequence)
comes from the content layer (content.loader) — never hardcoded here. The
trigger vocabulary is therefore the union of the content records' triggers,
not an independent list that could drift out of sync with the content.

Phase status semantics:
  completed — the phase's exit_trigger has been observed
  active    — the phase's entry_trigger has been observed, exit not yet
  upcoming  — neither observed
A trigger, once observed, stays observed (earliest occurrence wins).
Multiple phases can be active at once (e.g. contents inventory and the money
phase both begin when the carrier estimate arrives) — the UI renders them
side by side, not as a single "current" phase.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TypedDict

from src.content.models import ContentRecord

PhaseState = TypedDict("PhaseState", {
    "phase_id": str,
    "sequence": int,
    "status": str,             # completed | active | upcoming
    "entered_at": str | None,  # ISO timestamp of the entry event
    "exited_at": str | None,
    "typical_window_days": list[int] | None,
    "extended": bool,          # active and past typical window — informational
})


def _parse_ts(value: str | None) -> datetime | None:
    """Parse an ISO timestamp from the DB; tolerate a bare date string."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _event_map(events: list[dict]) -> dict[str, datetime]:
    """Earliest observed occurrence per trigger name, UTC-aware."""
    out: dict[str, datetime] = {}
    for event in events:
        name = event.get("trigger_name")
        ts = _as_utc_aware(_parse_ts(event.get("occurred_at")))
        if name is None or ts is None:
            continue
        if name not in out or ts < out[name]:
            out[name] = ts
    return out


def phase_status(
    record: ContentRecord,
    events_by_name: dict[str, datetime],
) -> str:
    """Classify one content phase against observed triggers."""
    entry = record.entry_trigger
    exit_ = record.exit_trigger
    if exit_ and exit_ in events_by_name:
        return "completed"
    if entry and entry in events_by_name:
        return "active"
    return "upcoming"


def compute_state(
    claim: dict,
    events: list[dict],
    records: list[ContentRecord],
    *,
    now: datetime | None = None,
) -> dict:
    """Compute the full claim state snapshot for a claim.

    ``claim``: claims row dict (must carry peril, date_of_loss, created_at).
    ``events``: claim_events rows for the claim.
    ``records``: active content records for the claim's peril (loader output).
    """
    ref = _as_utc_aware(now) or datetime.now(timezone.utc)
    peril = claim.get("peril") or "fire"
    records_for_peril = [r for r in records if peril in r.peril]
    records_for_peril.sort(key=lambda r: r.sequence)

    events_by_name = _event_map(events)

    phases: list[PhaseState] = []
    for record in records_for_peril:
        status = phase_status(record, events_by_name)
        entered: datetime | None = None
        exited: datetime | None = None
        if record.entry_trigger and record.entry_trigger in events_by_name:
            entered = events_by_name[record.entry_trigger]
        if record.exit_trigger and record.exit_trigger in events_by_name:
            exited = events_by_name[record.exit_trigger]
        extended = False
        if status == "active" and record.typical_window_days and entered is not None:
            lo, hi = record.typical_window_days
            days_since_entry = (ref.date() - entered.date()).days
            extended = days_since_entry > hi
        phases.append({
            "phase_id": record.phase_id,
            "sequence": record.sequence,
            "status": status,
            "entered_at": entered.isoformat() if entered else None,
            "exited_at": exited.isoformat() if exited else None,
            "typical_window_days": list(record.typical_window_days) if record.typical_window_days else None,
            "extended": extended,
        })

    active = [p for p in phases if p["status"] == "active"]
    completed = [p for p in phases if p["status"] == "completed"]
    entered_sequences = [p["sequence"] for p in phases if p["status"] in ("active", "completed")]
    current_sequence = max(entered_sequences) if entered_sequences else None
    current_phase = None
    if current_sequence is not None:
        # Prefer the earliest sequence among active; else the highest entered.
        actives = sorted(active, key=lambda p: p["sequence"])
        if actives:
            current_phase = actives[0]["phase_id"]
        elif completed:
            current_phase = max(completed, key=lambda p: p["sequence"])["phase_id"]

    loss_date = claim.get("date_of_loss")
    loss_date_str = loss_date if isinstance(loss_date, str) else (
        loss_date.isoformat() if isinstance(loss_date, date) else None
    )
    anchor = loss_date_str or None
    day_number: int | None = None
    if anchor:
        try:
            day_number = (ref.date() - date.fromisoformat(anchor)).days
        except ValueError:
            day_number = None
    else:
        created = _as_utc_aware(_parse_ts(claim.get("created_at")))
        if created is not None:
            day_number = (ref.date() - created.date()).days

    return {
        "peril": peril,
        "date_of_loss": anchor,
        "phase_count": len(records_for_peril),
        "current_phase": current_phase,
        "current_sequence": current_sequence,
        "day_number": day_number,
        "phases": phases,
        "active_phase_ids": [p["phase_id"] for p in active],
        "completed_phase_ids": [p["phase_id"] for p in completed],
    }


def trigger_vocabulary(records: list[ContentRecord]) -> set[str]:
    """The full set of phase trigger names the content layer defines."""
    vocab: set[str] = set()
    for record in records:
        if record.entry_trigger:
            vocab.add(record.entry_trigger)
        if record.exit_trigger:
            vocab.add(record.exit_trigger)
    return vocab
