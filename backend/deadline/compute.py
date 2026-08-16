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
    SERVICE_POSTED,
    SERVICE_PUBLICATION,
    SERVICE_UNKNOWN,
    Severity,
    florida_statewide_holidays,
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


def _add_calendar_period(
    start: date,
    years: int = 0,
    months: int = 0,
) -> date:
    """Add a calendar year/month period to a date.

    Handles leap-day correctly: Feb 29 + N years → Feb 28 in non-leap years.
    Month overflow (Jan 31 + 1 month) → last day of target month.

    Returns the anniversary date — e.g. 2023-03-01 + 1 year = 2024-03-01,
    NOT 2024-02-29 (which a 365-day offset would produce).
    """
    total_months = years * 12 + months
    if total_months == 0:
        return start

    target_year = start.year + (start.month + total_months - 1) // 12
    target_month = (start.month + total_months - 1) % 12 + 1

    import calendar as _cal
    max_day = _cal.monthrange(target_year, target_month)[1]
    target_day = min(start.day, max_day)

    return date(target_year, target_month, target_day)


def compute_deadline_for_event(
    rule_key: str,
    event_date: date,
    service_method: str,
    circuit: int | None,
    closure_dates: frozenset[date],   # statewide + per-circuit, fetched by caller
    has_local_closure_data: bool,     # False → escalate on fatal near unverified dates
    today: date | None = None,
    clerk_mailing_date: date | None = None,   # posted service (§ 48.183) only
) -> DeadlineComputationResult:
    """Compute all deadlines for one trigger event.

    Returns a DeadlineComputationResult. For ambiguous service methods
    (unknown/publication) two variants are computed and the earlier date wins.

    Posted service (§ 48.183) is handled separately (Decision 6): the
    effective service date is the LATER of the posting date (`event_date`)
    and the clerk's certificate-of-mailing date (`clerk_mailing_date`). If the
    mailing date is unknown, this escalates rather than computing from the
    posting date alone.
    """
    today = today or date.today()
    results: list[ComputedDeadline] = []
    escalation_reasons: list[str] = []

    # Statewide holidays (§ 110.117 / 2.514(a)(6)(A)) are generated in code for
    # any year, so computation never silently skips holidays just because the
    # court_closures table only has certain years seeded. The passed-in
    # closure_dates supplement with per-circuit/local closures. Day-counted
    # periods run at most ~40 days past the event, so event year + next year
    # covers every reachable date (including mail extension and roll-forward
    # across a year boundary).
    closure_dates = (
        closure_dates
        | florida_statewide_holidays(event_date.year)
        | florida_statewide_holidays(event_date.year + 1)
    )

    rule = RULES.get(rule_key)
    if rule is None:
        return DeadlineComputationResult(
            deadlines=[],
            escalation_needed=True,
            escalation_reasons=[f"Unknown rule key: {rule_key!r}"],
        )

    # Non-computable rules: the date is set by the court (e.g. printed on the
    # summons), so it cannot be derived from a rule period. Surface it as an
    # escalated deadline pointing the user to the document rather than dropping
    # it silently — "unknown" is a first-class output (Core Principle 5).
    # Calendar-year/month rules have response_days=None but response_years
    # or response_months set — those ARE computable.
    _has_calendar_period = (
        rule.get("response_years") or rule.get("response_months")
    )
    if rule["response_days"] is None and not _has_calendar_period:
        note = rule.get("note") or (
            "Date cannot be computed from a rule period — read the document."
        )
        results.append(ComputedDeadline(
            due_date=today,           # placeholder — the real date is on the document
            label=rule["label"],
            governing_rule=rule["governing_rule"],
            severity=rule["severity"],
            consequence=rule["consequence"],
            escalation_recommended=True,
            computation_trace=[{
                "step": 1,
                "action": (
                    f"{rule['label']}: date is set by the court and cannot be "
                    f"computed from a rule period — {note}"
                ),
                "date": None,
                "rule": rule["governing_rule"],
            }],
            assumption_disclosures=[note],
            is_past=False,
        ))
        return DeadlineComputationResult(
            deadlines=results,
            escalation_needed=True,
            escalation_reasons=[],
        )

    # Posted service (§ 48.183): effective date is the LATER of the posting
    # date and the clerk's certificate-of-mailing date. Never compute from the
    # posting date alone — a mailing date the clerk hasn't yet supplied could
    # push the true deadline later than a posting-only computation would show.
    if service_method == SERVICE_POSTED:
        if clerk_mailing_date is None:
            return DeadlineComputationResult(
                deadlines=[],
                escalation_needed=True,
                escalation_reasons=[
                    "Posted service under § 48.183 requires the clerk's "
                    "certificate-of-mailing date to compute the deadline. "
                    "That date has not been supplied — cannot compute from "
                    "the posting date alone. Manual review required."
                ],
            )
        effective_date = max(event_date, clerk_mailing_date)
        chosen = _compute_single(
            rule, effective_date, SERVICE_PERSONAL, circuit,
            closure_dates, has_local_closure_data, today,
            disclosure=(
                f"Posted service under § 48.183: computed from the later of "
                f"the posting date ({event_date}) and the clerk's "
                f"certificate-of-mailing date ({clerk_mailing_date})."
            ),
        )
        results.append(chosen)
    # For unknown/publication service, compute both personal and mail variants
    # and use the earlier (conservative) deadline.
    elif service_method in (SERVICE_UNKNOWN, SERVICE_PUBLICATION):
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

    response_days: int | None = rule.get("response_days")
    response_years: int | None = rule.get("response_years")
    response_months: int | None = rule.get("response_months")
    explicitly_business = rule["explicitly_business_days"]

    # ── Calendar year/month periods (statutory SOLs, not court deadlines) ──
    if response_years or response_months:
        raw_due = _add_calendar_period(
            event_date,
            years=response_years or 0,
            months=response_months or 0,
        )
        period_desc_parts = []
        if response_years:
            period_desc_parts.append(f"{response_years} calendar year(s)")
        if response_months:
            period_desc_parts.append(f"{response_months} calendar month(s)")
        period_desc = " + ".join(period_desc_parts)
        _t(
            f"Add {period_desc} to date of loss (anniversary date — "
            f"trigger day included per statutory convention)",
            raw_due,
            rule["governing_rule"],
        )
        # Statutory deadlines do NOT roll forward for weekends/holidays —
        # the anniversary date IS the deadline.
        final_due = raw_due
        _t(
            f"Statutory deadline: {final_due} (no weekend/holiday roll-forward)",
            final_due,
            rule["governing_rule"],
        )
    elif response_days is not None:
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
    else:
        # Should not reach here — caught by non-computable check above
        _t("ERROR: no computable period (days, years, or months)", None, "N/A")
        final_due = today

    _t(f"Final due date: {final_due}", final_due, rule["governing_rule"])

    # Past deadline flag
    is_past = final_due < today
    if is_past:
        disclosures.append(
            f"This deadline ({final_due}) has already passed as of {today}. "
            "Seek legal assistance immediately."
        )

    # Missing local closure data near a fatal COURT deadline → escalate rather
    # than assume the court was open (BUILD_PLAN Phase 4 failure mode #5).
    # Statutory SOL/anniversary deadlines (response_years/months) never consult
    # the closure calendar — no roll-forward — so this check does not apply.
    escalate = False
    uses_closure_calendar = not (response_years or response_months)
    if rule["severity"] == "fatal" and uses_closure_calendar and not has_local_closure_data:
        window_start = raw_due - timedelta(days=7)
        window_end = raw_due + timedelta(days=7)
        circuit_desc = f"circuit {circuit}" if circuit is not None else "this court (circuit unknown)"
        disclosures.append(
            f"No local court closure data is available for {circuit_desc}. "
            f"Statewide holidays were applied, but local closures near the due date "
            f"({window_start} – {window_end}) cannot be verified. Escalating."
        )
        escalate = True

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
