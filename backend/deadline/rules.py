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
    response_days: int | None         # None = court-set date, not computable
    day_counting: DayCounting | None
    explicitly_business_days: bool    # True = exclude weekends regardless of period length
    governing_rule: str               # citation — required
    severity: Severity
    consequence: str                  # plain-language — never a legal conclusion
    note: str | None                  # optional clarification


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
