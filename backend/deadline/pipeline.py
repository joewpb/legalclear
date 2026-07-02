"""Deadline pipeline orchestrator — Phase 4.

Stage 1 (LLM): extract trigger events via extract.py
Stage 2 (deterministic): compute deadlines via compute.py

The pipeline layer owns:
- Fetching court closure dates from the DB (so compute.py stays pure)
- Writing trigger_events and deadlines rows to the DB
- Escalation flag when severity=fatal and confidence<0.90
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import date

from src.memory.db import DatabaseManager

from .compute import compute_deadline_for_event
from .extract import extract_trigger_events
from .rules import RULES

logger = logging.getLogger(__name__)

ESCALATION_CONFIDENCE_THRESHOLD = 0.90  # fatal + below this → escalate


def _safe_int(value) -> int | None:
    """Best-effort int parse for LLM-supplied values (e.g. circuit numbers).

    Returns None if the value can't be interpreted as an int; the caller then
    treats the circuit as unknown (statewide closures still apply). Handles
    "13th" / "Circuit 13" -> 13; "Thirteenth" -> None.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        m = re.search(r"\d+", str(value))
        return int(m.group()) if m else None


def _safe_float(value, default: float = 0.0) -> float:
    """float() that won't raise on LLM output like confidence='high'."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


async def run_deadline_pipeline(
    document_id: str,
    document_text: str,
    db: DatabaseManager,
) -> dict:
    """Run the full two-stage deadline pipeline for a document.

    Returns a summary dict. Caller should check 'escalation_needed'.
    """
    result = {
        "document_id": document_id,
        "trigger_events_written": 0,
        "deadlines_written": 0,
        "escalation_needed": False,
        "escalation_reasons": [],
    }

    # ── Stage 1: LLM extraction ───────────────────────────────────────────────
    extraction = await extract_trigger_events(document_text)

    if extraction.get("escalation_needed"):
        result["escalation_needed"] = True
        reason = extraction.get("escalation_reason") or "Extraction failed"
        result["escalation_reasons"].append(reason)

    events = extraction.get("events", [])
    if not events:
        return result

    # ── Fetch court closure dates from DB (used by every deadline computation) ─
    # Always fetch statewide (circuit=0) + the specific circuit if known
    circuits_needed = {0}
    for ev in events:
        c = _safe_int(ev.get("circuit"))
        if c is not None:
            circuits_needed.add(c)

    closure_dates: frozenset[date] = frozenset()
    if db.client is not None:
        try:
            rows = (db.client.table("court_closures")
                    .select("circuit,closure_date")
                    .in_("circuit", list(circuits_needed))
                    .execute())
            closure_dates = frozenset(
                date.fromisoformat(r["closure_date"])
                for r in (rows.data or [])
            )
        except Exception as e:
            logger.error("Failed to fetch court closures: %s", e)

    # ── Stage 2: deterministic computation + DB writes ────────────────────────
    for event in events:
        rule_key = event.get("document_type", "unknown")
        event_date_str = event.get("event_date")
        service_method = event.get("service_method", "unknown")
        confidence = _safe_float(event.get("confidence"))
        circuit = _safe_int(event.get("circuit"))

        # Missing service date → escalate immediately
        if not event_date_str:
            result["escalation_needed"] = True
            result["escalation_reasons"].append(
                f"Service/event date could not be extracted for {rule_key!r}. "
                "Manual review required to determine the applicable deadline."
            )
            # Still write the trigger event for audit purposes
            _write_trigger_event(db, document_id, event, is_escalated=True)
            result["trigger_events_written"] += 1
            continue

        # Unknown document type → escalate
        if rule_key == "unknown" or rule_key not in RULES:
            result["escalation_needed"] = True
            result["escalation_reasons"].append(
                f"Document type could not be determined (got {rule_key!r}). "
                "Manual review required."
            )
            _write_trigger_event(db, document_id, event, is_escalated=True)
            result["trigger_events_written"] += 1
            continue

        # Malformed event date → escalate this event rather than 500 the request
        try:
            event_date = date.fromisoformat(event_date_str)
        except ValueError:
            result["escalation_needed"] = True
            result["escalation_reasons"].append(
                f"The event date for {rule_key!r} could not be parsed "
                f"({event_date_str!r}). Manual review required to compute the deadline."
            )
            _write_trigger_event(db, document_id, event, is_escalated=True)
            result["trigger_events_written"] += 1
            continue

        compute_result = compute_deadline_for_event(
            rule_key=rule_key,
            event_date=event_date,
            service_method=service_method,
            circuit=circuit,
            closure_dates=closure_dates,
            has_local_closure_data=bool(closure_dates),
        )

        # Write trigger_event row
        trigger_id = _write_trigger_event(db, document_id, event)
        result["trigger_events_written"] += 1

        # Write deadline rows
        for deadline in compute_result.deadlines:
            rule = RULES.get(rule_key, {})

            # Escalate fatal deadlines below confidence threshold
            should_escalate = (
                deadline.escalation_recommended
                or (rule.get("severity") == "fatal" and confidence < ESCALATION_CONFIDENCE_THRESHOLD)
            )
            if should_escalate:
                result["escalation_needed"] = True
                if confidence < ESCALATION_CONFIDENCE_THRESHOLD and rule.get("severity") == "fatal":
                    result["escalation_reasons"].append(
                        f"Fatal deadline {deadline.label!r} has extraction confidence "
                        f"{confidence:.0%} (below {ESCALATION_CONFIDENCE_THRESHOLD:.0%} threshold)."
                    )
                result["escalation_reasons"].extend(deadline.assumption_disclosures)

            if db.client is not None:
                try:
                    db.client.table("deadlines").insert({
                        "document_id": document_id,
                        "trigger_event_id": trigger_id,
                        "label": deadline.label,
                        "due_date": deadline.due_date.isoformat(),
                        "governing_rule": deadline.governing_rule,
                        "consequence_if_missed": deadline.consequence,
                        "severity": deadline.severity,
                        "confidence": confidence,
                        "escalation_recommended": should_escalate,
                        "computation_trace": deadline.computation_trace,
                        "reminder_state": "pending",
                    }).execute()
                    result["deadlines_written"] += 1
                except Exception as e:
                    logger.error("Failed to write deadline: %s", e)

        if compute_result.escalation_needed:
            result["escalation_needed"] = True
            result["escalation_reasons"].extend(compute_result.escalation_reasons)

    return result


def _write_trigger_event(
    db: DatabaseManager,
    document_id: str,
    event: dict,
    is_escalated: bool = False,
) -> str | None:
    """Write a trigger_event row and return its id."""
    if db.client is None:
        return None
    try:
        row = {
            "document_id": document_id,
            "event_type": event.get("event_type", "unknown"),
            "event_date": event.get("event_date") or "1970-01-01",  # placeholder for null
            "service_method": event.get("service_method", "unknown"),
            "document_type": event.get("document_type", "unknown"),
            "jurisdiction": event.get("jurisdiction", "FL"),
            "circuit": event.get("circuit"),
            "county": event.get("county"),
            "case_number": event.get("case_number"),
            "raw_text_excerpt": event.get("raw_text_excerpt", ""),
            "confidence": float(event.get("confidence", 0.0)),
        }
        result = db.client.table("trigger_events").insert(row).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.error("Failed to write trigger_event: %s", e)
        return None
