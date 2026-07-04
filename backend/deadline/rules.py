"""Florida deadline rule library — Phase 4.

Every rule must cite its source. Never ship a rule without a citation.
This module is pure data — no LLM, no I/O, no date arithmetic.

Versioned: bump RULES_VERSION when any rule is added or changed.
"""

from __future__ import annotations

from typing import Literal, TypedDict

RULES_VERSION = "2026-05-19-v1"

Severity = Literal["fatal", "high", "medium", "low"]
DayCounting = Literal["calendar", "business"]


class DeadlineRule(TypedDict):
    label: str
    response_days: int | None
    response_years: int | None
    response_months: int | None
    deadline_type: str                  # "SOL" | "insurer_deadline" | "pre_suit_gate" | "court_filing"
    day_counting: DayCounting | None
    explicitly_business_days: bool
    governing_rule: str
    severity: Severity
    consequence: str
    note: str | None


# fmt: off
RULES: dict[str, DeadlineRule] = {

    "civil_summons": {
        "label":                    "Answer to Civil Summons",
        "response_days":            20,
        "day_counting":             "calendar",   # ≥7 days → calendar per 2.514
        "explicitly_business_days": False,
        "governing_rule":           "Fla. R. Civ. P. 1.140(a)",
        "severity":                 "fatal",
        "consequence": (
            "A default judgment may be entered against you if you do not "
            "file a written response within 20 days of service."
        ),
        "note": None,
    },

    "eviction_complaint": {
        "label":                    "Answer to Residential Eviction Complaint",
        "response_days":            5,
        "day_counting":             "business",   # statute says "5 business days"
        "explicitly_business_days": True,
        "governing_rule":           "Fla. Stat. § 83.60(2)",
        "severity":                 "fatal",
        "consequence": (
            "A default judgment for eviction and possession may be entered "
            "if you do not file a written response within 5 business days."
        ),
        "note": None,
    },

    "foreclosure_complaint": {
        "label":                    "Answer to Foreclosure Complaint",
        "response_days":            20,
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. R. Civ. P. 1.140(a)",
        "severity":                 "fatal",
        "consequence": (
            "A default judgment of foreclosure may be entered if you do not "
            "file a written response within 20 days of service."
        ),
        "note": None,
    },

    "family_law_petition": {
        "label":                    "Answer to Family Law Petition",
        "response_days":            20,
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Fam. L. R. P. 12.140",
        "severity":                 "fatal",
        "consequence": (
            "The court may grant the petition by default if you do not "
            "file a written response within 20 days of service."
        ),
        "note": None,
    },

    "small_claims_summons": {
        "label":                    "Small Claims Pretrial Conference",
        "response_days":            None,          # date is on the summons, set by clerk
        "day_counting":             None,
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Sm. Cl. R. 7.090",
        "severity":                 "high",
        "consequence": (
            "You must appear at the pretrial conference date shown on your summons. "
            "Failure to appear may result in a default judgment against you."
        ),
        "note": (
            "The pretrial conference date is set by the clerk at the time of filing "
            "and printed on the summons. It cannot be computed from a rule period — "
            "read the date on your summons."
        ),
    },

    "notice_of_appeal": {
        "label":                    "Notice of Appeal",
        "response_days":            30,
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. R. App. P. 9.110(b)",
        "severity":                 "fatal",
        "consequence": (
            "You will lose your right to appeal if you do not file a notice "
            "of appeal within 30 days of the rendition of the final order."
        ),
        "note": (
            "The 30-day clock runs from the date the order is rendered (signed and "
            "filed with the clerk), not from the date you received it."
        ),
    },

    "motion_for_rehearing": {
        "label":                    "Motion for Rehearing",
        "response_days":            15,
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. R. Civ. P. 1.530(b)",
        "severity":                 "high",
        "consequence": (
            "You will waive your right to seek rehearing if you do not file "
            "a motion within 15 days of the order."
        ),
        "note": None,
    },

    "discovery_request": {
        "label":                    "Response to Discovery Request",
        "response_days":            30,
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. R. Civ. P. 1.340(a)",
        "severity":                 "medium",
        "consequence": (
            "Failure to respond to a discovery request within 30 days may result "
            "in court sanctions or the facts being deemed admitted."
        ),
        "note": None,
    },

    # ── Property & Casualty — Module 5 ─────────────────────────────────
    # Statutory insurance deadlines. Computed as calendar days (not 2.514
    # business days) — these are NOT court filing deadlines.

    "pc_report_claim": {
        "label":                    "Report Property Insurance Claim",
        "response_days":            None,
        "response_years":           1,
        "response_months":          None,
        "deadline_type":            "SOL",
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Stat. § 627.70132",
        "severity":                 "fatal",
        "consequence": (
            "A claim not reported within 1 year of the date of loss is barred. "
            "This deadline runs from the date of loss, not from discovery."
        ),
        "note": "For weather events, date of loss is hurricane landfall or NOAA-verified date per § 627.70132(3).",
    },

    "pc_supplemental_claim": {
        "label":                    "Report Supplemental Property Claim",
        "response_days":            None,
        "response_years":           None,
        "response_months":          18,
        "deadline_type":            "SOL",
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Stat. § 627.70132",
        "severity":                 "fatal",
        "consequence": (
            "A supplemental claim for additional damage from the same event "
            "must be reported within 18 months of the date of loss."
        ),
        "note": None,
    },

    "pc_file_suit": {
        "label":                    "File Suit — Breach of Property Insurance Contract",
        "response_days":            None,
        "response_years":           5,
        "response_months":          None,
        "deadline_type":            "SOL",
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Stat. § 95.11(2)(e)",
        "severity":                 "fatal",
        "consequence": (
            "A lawsuit for breach of the property insurance contract must be "
            "filed within 5 years of the date of loss. If missed, the suit is "
            "time-barred. This deadline is independent of the claim-reporting "
            "deadline — both must be satisfied."
        ),
        "note": (
            "This 5-year period runs from the date of loss (not date of breach). "
            "Filing mediation or a Civil Remedy Notice does NOT toll this clock."
        ),
    },

    "pc_pay_or_deny": {
        "label":                    "Insurer Pay-or-Deny Deadline",
        "response_days":            60,
        "response_years":           None,
        "response_months":          None,
        "deadline_type":            "insurer_deadline",
        "day_counting":             "calendar",
        "explicitly_business_days": False,
        "governing_rule":           "Fla. Stat. § 627.70131(7)(a)",
        "severity":                 "high",
        "consequence": (
            "The insurer must pay or deny the claim, or pay the undisputed "
            "portion, within 60 days after notice of the claim. If the deadline "
            "is missed, interest accrues from the date of notice at the § 55.03 rate."
        ),
        "note": (
            "The 60-day period may be extended for factors beyond the insurer's "
            "control or after a declared state of emergency."
        ),
    },

    "pc_notice_of_intent": {
        "label":                    "Pre-Suit Notice of Intent to Initiate Litigation",
        "response_days":            10,
        "response_years":           None,
        "response_months":          None,
        "deadline_type":            "pre_suit_gate",
        "day_counting":             "business",
        "explicitly_business_days": True,
        "governing_rule":           "Fla. Stat. § 627.70152",
        "severity":                 "fatal",
        "consequence": (
            "A lawsuit filed without first serving the Notice of Intent to "
            "Initiate Litigation under § 627.70152 is subject to dismissal "
            "regardless of the merits. The notice must be filed at least 10 "
            "business days before filing suit."
        ),
        "note": (
            "Filed through the DFS online portal. The notice must be served "
            "within the § 95.11 limitations period."
        ),
    },
}
# fmt: on

# All document_type values the extractor may return
KNOWN_DOCUMENT_TYPES: frozenset[str] = frozenset(RULES.keys()) | {"unknown"}

# Service method constants
SERVICE_PERSONAL    = "personal"
SERVICE_MAIL        = "mail"
SERVICE_ESERVICE    = "e_service"
SERVICE_PUBLICATION = "publication"
SERVICE_UNKNOWN     = "unknown"

MAIL_EXTENSION_DAYS = 5   # Fla. R. Gen. Prac. & Jud. Admin. 2.514(c)
