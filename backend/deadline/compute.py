"""Deterministic deadline computation — Phase 4.

Implements Fla. R. Gen. Prac. & Jud. Admin. 2.514.

CRITICAL INVARIANTS:
- This module does NO LLM calls.
- This module does NO database calls.
- All date arithmetic lives here and ONLY here.
- `closure_dates` is fetched by the caller (pipeline.py) and passed in.

Every result carries a `computation_trace` — an ordered list of steps,
each with the date at that step and the rule citation that justifies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .rules import (
    MAIL_EXTENSION_DAYS,
    RULES,
    SERVICE_ESERVICE,
    SERVICE_MAIL,
    SERVICE_PERSONAL,
    SERVICE_PUBLICATION,
    SERVICE_UNKNOWN,
    Severity,
)

RULE_2514      = "Fla. R. Gen. Prac. & Jud. Admin. 2.514"
RULE_2514_A    = "Fla. R. Gen. Prac. & Jud. Admin. 2.514(a) — exclude trigger day"
RULE_2514_B1   = "Fla. R. Gen. Prac. & Jud. Admin. 2.514 — periods <7 days exclude weekends/holidays"
RULE_2514_B2   = "Fla. R. Gen. Prac. & Jud. Admin. 2.514 — periods ≥7 days count calendar days"
RULE_2514_C    = "Fla. R. Gen. Prac. & Jud. Admin. 2.514(c) — mail service adds 5 days"
RULE_2514_ROLL = "Fla. R. Gen. Prac. & Jud. Admin. 2.514 — endpoint on weekend/holiday rolls forward"


@dataclass
class ComputedDeadline:
    due_date: date
    label: str
    governing_rule: str
    severity: Severity
    consequence: str
    escalation_recommended: bool
    computation_trace: list[dict[str, Any]]
    assumption_disclosures: list[str]
    is_past: bool


@dataclass
class DeadlineComputationResult:
    deadlines: list[ComputedDeadline]
    escalation_needed: bool
    escalation_reasons: list[str]


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # 5=Saturday, 6=Sunday


def _is_holiday(d: date, closure_dates: frozenset[date]) -> bool:
    return d in closure_dates


def _is_closed(d: date, closure_dates: frozenset[date]) -> bool:
    return _is_weekend(d) or _is_holiday(d, closure_dates)


def _next_business_day(d: date, closure_dates: frozenset[date]) -> date:
    """Return d if it is a business day, otherwise the next business day."""
    while _is_closed(d, closure_dates):
        d += timedelta(days=1)
    return d


def _add_business_days(start: date, n: int,
                       closure_dates: frozenset[date]) -> date:
    """Count n business days forward from start (start is day 0, not counted)."""
    current = start
    counted = 0
    while counted < n:
        current += timedelta(days=1)
        if not _is_closed(current, closure_dates):
            counted += 1
    return current


def _add_calendar_days(start: date, n: int) -> date:
    return start + timedelta(days=n)


def compute_deadline_for_event(
    rule_key: str,
    event_date: date,
    service_method: str,
    circuit: int | None,
    closure_dates: frozenset[date],   # statewide + per-circuit, fetched by caller
    has_local_closure_data: bool,     # False → escalate on fatal near unverified dates
    today: date | None = None,
) -> DeadlineComputationResult:
    """Compute all deadlines for one trigger event.

    Returns a DeadlineComputationResult. For ambiguous service methods
    (unknown/publication) two variants are computed and the earlier date wins.
    """
    today = today or date.today()
    results: list[ComputedDeadline] = []
    escalation_reasons: list[str] = []

    rule = RULES.get(rule_key)
    if rule is None:
        return DeadlineComputationResult(
            deadlines=[],
            escalation_needed=True,
            escalation_reasons=[f"Unknown rule key: {rule_key!r}"],
        )

    # Small claims: date is on the summons — not computable
    if rule["response_days"] is None:
        results.append(ComputedDeadline(
            due_date=today,           # placeholder — real date is on the document
            label=rule["label"],
            governing_rule=rule["governing_rule"],
            severity=rule["severity"],
            consequence=rule["consequence"],
            escalation_recommended=True,
            computation_trace=[{
                "step": 1,
                "action": "Pretrial conference date is printed on the summons — cannot be computed",
                "date": None,
                "rule": rule["governing_rule"],
            }],
            assumption_disclosures=["Pretrial conference date must be read from the summons."],
            is_past=False,
        ))
        return DeadlineComputationResult(
            deadlines=results, escalation_needed=False, escalation_reasons=[]
        )

    # For unknown/publication service, compute both personal and mail variants
    # and use the earlier (conservative) deadline.
    if service_method in (SERVICE_UNKNOWN, SERVICE_PUBLICATION):
        personal_result = _compute_single(
            rule, event_date, SERVICE_PERSONAL, circuit,
            closure_dates, has_local_closure_data, today,
            disclosure="Service method was unclear; using personal-service period (shorter) — verify the actual service method."
        )
        mail_result = _compute_single(
            rule, event_date, SERVICE_MAIL, circuit,
            closure_dates, has_local_closure_data, today,
            disclosure=None
        )
        # Use the earlier (more conservative) date
        chosen = personal_result if personal_result.due_date <= mail_result.due_date else mail_result
        chosen.assumption_disclosures.append(
            f"Service method was {service_method!r}. "
            "Computed both personal-service and mail-service variants; "
            f"using earlier date ({chosen.due_date}) to be conservative. "
            "Verify the actual service method with the original document."
        )
        results.append(chosen)
    else:
        results.append(_compute_single(
            rule, event_date, service_method, circuit,
            closure_dates, has_local_closure_data, today,
        ))

    # Aggregate escalation across all computed deadlines
    all_escalate = any(d.escalation_recommended for d in results)
    for d in results:
        escalation_reasons.extend(
            d.assumption_disclosures
            if d.escalation_recommended and d.assumption_disclosures
            else []
        )

    return DeadlineComputationResult(
        deadlines=results,
        escalation_needed=all_escalate,
        escalation_reasons=escalation_reasons,
    )


def _compute_single(
    rule: dict,
    event_date: date,
    service_method: str,
    circuit: int | None,
    closure_dates: frozenset[date],
    has_local_closure_data: bool,
    today: date,
    disclosure: str | None = None,
) -> ComputedDeadline:
    trace: list[dict[str, Any]] = []
    disclosures: list[str] = []
    step = 1

    def _t(action: str, d: date | None, rule_ref: str) -> None:
        nonlocal step
        trace.append({
            "step": step,
            "action": action,
            "date": d.isoformat() if d else None,
            "rule": rule_ref,
        })
        step += 1

    _t(f"Trigger event date: {event_date}", event_date, rule["governing_rule"])

    # Mail service extension — applied BEFORE counting the period
    adjusted_start = event_date
    if service_method == SERVICE_MAIL:
        adjusted_start = event_date + timedelta(days=MAIL_EXTENSION_DAYS)
        _t(
            f"Mail service: add {MAIL_EXTENSION_DAYS} days to start date",
            adjusted_start,
            RULE_2514_C,
        )

    # Exclude the trigger/start day (day 0 is not counted)
    _t(
        "Exclude trigger day — counting begins the following day",
        adjusted_start + timedelta(days=1),
        RULE_2514_A,
    )

    response_days: int = rule["response_days"]
    explicitly_business = rule["explicitly_business_days"]
    use_business_days = explicitly_business or response_days < 7

    if use_business_days:
        rule_ref = (
            RULE_2514_B1 if not explicitly_business
            else f"{rule['governing_rule']} (explicitly business days)"
        )
        raw_due = _add_business_days(adjusted_start, response_days, closure_dates)
        _t(
            f"Count {response_days} business days (weekends/holidays excluded)",
            raw_due,
            rule_ref,
        )
    else:
        raw_due = _add_calendar_days(adjusted_start + timedelta(days=1), response_days - 1)
        _t(
            f"Count {response_days} calendar days",
            raw_due,
            RULE_2514_B2,
        )

    # Roll forward if endpoint is weekend or holiday
    final_due = _next_business_day(raw_due, closure_dates)
    if final_due != raw_due:
        _t(
            f"Raw due date {raw_due} falls on {'weekend' if _is_weekend(raw_due) else 'holiday'}; "
            f"rolling forward to next business day",
            final_due,
            RULE_2514_ROLL,
        )
    else:
        _t("Due date falls on a business day — no roll-forward needed", final_due, RULE_2514)

    _t(f"Final due date: {final_due}", final_due, rule["governing_rule"])

    # Past deadline flag
    is_past = final_due < today
    if is_past:
        disclosures.append(
            f"This deadline ({final_due}) has already passed as of {today}. "
            "Seek legal assistance immediately."
        )

    # Missing local closure data near a fatal deadline
    escalate = False
    if rule["severity"] == "fatal":
        if not has_local_closure_data:
            window_start = raw_due - timedelta(days=7)
            window_end = raw_due + timedelta(days=7)
            disclosures.append(
                f"No local court closure data is available for circuit {circuit}. "
                f"Cannot verify whether the court near the due date "
                f"({window_start} – {window_end}) was open. Escalating."
            )
            escalate = True
        if rule["severity"] == "fatal" and False:  # confidence check handled in pipeline
            pass

    if disclosure:
        disclosures.append(disclosure)

    return ComputedDeadline(
        due_date=final_due,
        label=rule["label"],
        governing_rule=rule["governing_rule"],
        severity=rule["severity"],
        consequence=rule["consequence"],
        escalation_recommended=escalate or is_past,
        computation_trace=trace,
        assumption_disclosures=disclosures,
        is_past=is_past,
    )
