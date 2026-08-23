"""I-6 — deterministic red-flag detector (Phase I finale, 2026-08-23).

Spec: docs/pc-claim-guide-module.md §5. Two or more active flags -> an
escalation banner recommending independent representation. No LLM.

Two flag classes:
  user-declared — the user tells us the signal happened (recorded as a
                  claim_event with a red-flag trigger name).
  derived       — computed deterministically from event timestamps. These
                  are observation heuristics, NOT legal deadlines; they
                  never produce a due date of any kind.

The financial-records special screen ships with the spec's authored text
verbatim (see runs/phase-i-autonomous/LOG.md D3 — attorney review item in
the final report).

Disclaimer contract: this module emits no standalone user-facing prose —
its escalation payload is wrapped by the canonical ``apply_disclaimer``
(src/core/upl.py) at the claims router boundary, and the Claim Guide page
renders the persistent disclaimer on every view.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

Flag = TypedDict("Flag", {
    "name": str,
    "label": str,
    "description": str,
    "source": str,  # user | derived
})

# ── user-declared flags (spec §5 list, in spec order) ───────────────────

USER_DECLARED_FLAGS: list[Flag] = [
    {"name": "reservation_of_rights_letter",
     "label": "Reservation of rights letter",
     "description": "A letter from the insurer using the words 'reservation of rights' means it is preserving the right to deny the claim.",
     "source": "user"},
    {"name": "recorded_statement_re_requested",
     "label": "Recorded statement requested again",
     "description": "The insurer has asked for a recorded statement a second time.",
     "source": "user"},
    {"name": "siu_contact",
     "label": "Contact from a special investigator",
     "description": "The insurer's SIU or a 'special investigator' has made contact.",
     "source": "user"},
    {"name": "financial_records_demanded",
     "label": "Financial records demanded",
     "description": "The insurer asked for tax returns, bank statements, or a blank financial authorization.",
     "source": "user"},
    {"name": "euo_demanded",
     "label": "Examination Under Oath demanded",
     "description": "An examination under oath has been demanded, especially by an outside law firm.",
     "source": "user"},
    {"name": "engineer_retained",
     "label": "Insurer retained an engineer",
     "description": "The insurer retained an engineer or origin-and-cause expert.",
     "source": "user"},
    {"name": "third_adjuster_assigned",
     "label": "Third adjuster assigned",
     "description": "A third adjuster has been assigned to the claim within 60 days.",
     "source": "user"},
    {"name": "estimate_omits_scope",
     "label": "Estimate omits documented scope",
     "description": "The insurer's estimate omits damage the household's own contractor documented.",
     "source": "user"},
    {"name": "full_and_final_check",
     "label": "Check marked 'full and final'",
     "description": "A check arrived annotated 'full and final' settlement.",
     "source": "user"},
]

# ── derived flags ────────────────────────────────────────────────────────

_DERIVED_FLAG_DEFS: list[Flag] = [
    {"name": "no_estimate_7d_after_inspection",
     "label": "No written estimate 7+ days after inspection",
     "description": "The inspection happened more than 7 days ago and no written estimate has been recorded.",
     "source": "derived"},
    {"name": "silence_past_day_60",
     "label": "Silence past day 60",
     "description": "More than 60 days have passed since the claim was reported with no payment, denial, or resolution recorded.",
     "source": "derived"},
]

ALL_FLAGS: dict[str, Flag] = {f["name"]: f for f in USER_DECLARED_FLAGS + _DERIVED_FLAG_DEFS}

USER_DECLARED_FLAG_NAMES: frozenset[str] = frozenset(f["name"] for f in USER_DECLARED_FLAGS)
DERIVED_FLAG_NAMES: frozenset[str] = frozenset(f["name"] for f in _DERIVED_FLAG_DEFS)

# ── financial-records special screen (spec §5, authored copy — verbatim) ─

FINANCIAL_RECORDS_SCREEN = (
    "Insurers investigating a fire look for a financial motive. They may ask "
    "for bank statements, tax returns, and signed authorizations to pull "
    "credit and records. Refusing outright can breach the policy's "
    "cooperation clause and sink the claim — courts have held the Fifth "
    "Amendment does not excuse a policyholder from an Examination Under "
    "Oath. Do not refuse. Do not sign a blank authorization either. Talk "
    "to an attorney about narrowing what you produce."
)

ESCALATION_BANNER = (
    "Two or more of the signals that often appear when a claim is headed "
    "toward a dispute are present on this claim. Many people at this stage "
    "have an independent professional review the file — a licensed Florida "
    "attorney or public adjuster. Free and low-cost help:"
)

_RESOURCE_LINKS = [{"label": "Find free legal help", "url": "/find-legal-help"}]


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _first_occurrence(events: list[dict], name: str) -> datetime | None:
    found: datetime | None = None
    for event in events:
        if event.get("trigger_name") != name:
            continue
        ts = _as_utc(_parse_ts(event.get("occurred_at")))
        if ts is None:
            continue
        if found is None or ts < found:
            found = ts
    return found


def user_declared_flags(events: list[dict]) -> list[Flag]:
    """Flags the user recorded as claim events, deduplicated."""
    names = {event.get("trigger_name") for event in events} & set(USER_DECLARED_FLAG_NAMES)
    return [USER_DECLARED_FLAGS_BY_NAME[n] for n in sorted(names) if n in USER_DECLARED_FLAGS_BY_NAME]


USER_DECLARED_FLAGS_BY_NAME: dict[str, Flag] = {f["name"]: f for f in USER_DECLARED_FLAGS}


def derived_flags(events: list[dict], *, now: datetime | None = None) -> list[Flag]:
    """Compute the two observation-heuristic flags from event timestamps."""
    ref = _as_utc(now) or datetime.now(timezone.utc)
    out: list[Flag] = []

    inspection = _first_occurrence(events, "adjuster_inspection_scheduled")
    estimate = _first_occurrence(events, "carrier_estimate_received")
    if inspection is not None and estimate is None and (ref - inspection).days >= 7:
        out.append(ALL_FLAGS["no_estimate_7d_after_inspection"])

    reported = _first_occurrence(events, "claim_number_received")
    closed_signals = ("payment_received", "claim_denied_or_underpaid", "resolved_or_suit_filed")
    if reported is not None and (ref - reported).days >= 60:
        if not any(_first_occurrence(events, name) is not None for name in closed_signals):
            out.append(ALL_FLAGS["silence_past_day_60"])

    return out


def active_flags(events: list[dict], *, now: datetime | None = None) -> list[Flag]:
    """Union of user-declared and derived flags."""
    return user_declared_flags(events) + derived_flags(events, now=now)


def escalation(flags: list[Flag]) -> dict | None:
    """Two or more active flags -> escalation payload with the special-case
    financial screen when that flag is among them. None otherwise."""
    if len(flags) < 2:
        return None
    has_financial = any(f["name"] == "financial_records_demanded" for f in flags)
    return {
        "type": "red_flag_escalation",
        "active_count": len(flags),
        "flags": flags,
        "banner": ESCALATION_BANNER,
        "show_financial_screen": has_financial,
        "financial_screen_text": FINANCIAL_RECORDS_SCREEN if has_financial else None,
        "resource_links": _RESOURCE_LINKS,
    }
