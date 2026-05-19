"""CaseContext schema for the Police Report Analyzer — Phase 9.

Mirrors frontend/src/components/policereport/types.ts field-for-field.
The source of truth for the shape is the TypeScript interface; this module
must track it. Do NOT add fields. Do NOT put legal conclusions here.
"""
from __future__ import annotations


def empty_case_context() -> dict:
    """Return a zeroed CaseContext dict.

    Mirrors createEmptyCaseContext() in types.ts exactly.
    Used as the fail-soft fallback in extract_case_context.
    """
    return {
        "routing": {
            "userRole": "unclear",
            "reportType": "unknown",
            "routingConfidence": 0,
        },
        "document": {
            "agency": None,
            "reportNumber": None,
            "reportDate": None,
            "extractionConfidence": 0,
        },
        "incident": {
            "incidentDateTime": None,
            "incidentLocation": None,
            "incidentType": None,
            "charges": [],
            "statuteReferences": [],
        },
        "rightsEvents": {
            "arrestMade": False,
            "searchOccurred": False,
            "searchContext": None,
            "mirandaMentioned": False,
            "custodialIndicators": [],
            "statementsAttributed": False,
        },
        "people": {
            "officers": [],
            "otherPartiesCount": 0,
        },
        "discrepancies": [],
        "sensitivity": {
            "domesticViolence": False,
            "sexualOffense": False,
            "juvenileInvolved": False,
        },
        "derived": {
            "timelineStage": None,
            "deadlines": [],
            "questionsForCounsel": [],
            "collateralConsequenceFlags": [],
        },
    }
