"""Phase 5 — Classification router.

Pure Python — no LLM, no DB. Maps a classification result to:
  - deadline_rule_keys: which Phase 4 rules apply
  - suggested_form_tags: situation_tags to query in court_forms
  - escalate: True for criminal/expungement or truly unknown
  - requires_human_review: True for low-confidence (caller must surface dropdown)

The rule is: a low-confidence classification must NOT silently drive a deadline
computation. The pipeline layer enforces this before calling the deadline engine.
"""

from __future__ import annotations

from typing import TypedDict

# Maps triage document_type → Phase 4 deadline rule key(s).
# None means no computable deadline rule — may still surface forms.
# Multiple keys mean several clocks could start (e.g. judgment → appeal + rehearing).
DOC_TYPE_TO_DEADLINE_RULES: dict[str, list[str]] = {
    "civil_summons":          ["civil_summons"],
    "eviction_complaint":     ["eviction_complaint"],
    "foreclosure_complaint":  ["foreclosure_complaint"],
    "family_law_petition":    ["family_law_petition"],
    "small_claims_summons":   ["small_claims_summons"],
    "motion":                 ["motion_for_rehearing"],  # most motions trigger response clock
    "order":                  [],                        # depends on order type; human review
    "judgment":               ["notice_of_appeal", "motion_for_rehearing"],
    "notice_of_hearing":      [],                        # hearing date is on the notice
    "discovery_request":      ["discovery_request"],
    "criminal":               [],   # → escalation; no deadline computation
    "expungement":            [],   # → escalation per v2 scope decision
    "unknown":                [],   # → human review
}

# Maps triage document_type → situation_tags to query court_forms.
DOC_TYPE_TO_FORM_TAGS: dict[str, list[str]] = {
    "civil_summons":          ["service", "summons"],
    "eviction_complaint":     [],          # eviction forms not yet in catalog
    "foreclosure_complaint":  [],
    "family_law_petition":    ["divorce"],
    "small_claims_summons":   [],          # small claims forms not yet in catalog
    "motion":                 [],
    "order":                  [],
    "judgment":               ["divorce"],  # dissolution judgments → family law forms
    "notice_of_hearing":      [],
    "discovery_request":      [],
    "criminal":               [],
    "expungement":            [],
    "unknown":                [],
}

# Always escalate these document types — no deadline computation, no form surfacing.
ALWAYS_ESCALATE_TYPES: frozenset[str] = frozenset({"criminal", "expungement"})

CONFIDENCE_THRESHOLD = 0.70  # must match classify.py


class RoutingResult(TypedDict):
    deadline_rule_keys: list[str]
    suggested_form_tags: list[str]
    escalate: bool
    escalation_reason: str | None
    requires_human_review: bool
    review_reason: str | None
    safe_to_auto_compute: bool   # True only when confident AND not escalating


def route(classification: dict) -> RoutingResult:
    """Return routing instructions for a classification result.

    This is the gate that prevents low-confidence classifications from
    silently driving deadline computations.
    """
    doc_type: str = classification.get("document_type", "unknown")
    confidence: float = float(classification.get("document_type_confidence", 0.0))
    is_criminal: bool = bool(classification.get("is_criminal", False))
    is_expungement: bool = bool(classification.get("is_expungement", False))
    requires_review: bool = bool(classification.get("requires_human_review", False))

    # Criminal or expungement → escalate immediately
    if is_criminal or is_expungement or doc_type in ALWAYS_ESCALATE_TYPES:
        reason = (
            "This document relates to a criminal matter or expungement. "
            "LegalClear does not provide analysis for criminal matters. "
            "Please consult a licensed Florida attorney."
        )
        return RoutingResult(
            deadline_rule_keys=[],
            suggested_form_tags=[],
            escalate=True,
            escalation_reason=reason,
            requires_human_review=False,
            review_reason=None,
            safe_to_auto_compute=False,
        )

    # Low confidence or unknown → human review required, no auto-computation
    if requires_review or confidence < CONFIDENCE_THRESHOLD or doc_type == "unknown":
        return RoutingResult(
            deadline_rule_keys=DOC_TYPE_TO_DEADLINE_RULES.get(doc_type, []),
            suggested_form_tags=DOC_TYPE_TO_FORM_TAGS.get(doc_type, []),
            escalate=False,
            escalation_reason=None,
            requires_human_review=True,
            review_reason=classification.get("review_reason") or (
                f"Document type '{doc_type}' has confidence {confidence:.0%}. "
                "Please confirm before deadlines are computed."
            ),
            safe_to_auto_compute=False,
        )

    # Confident classification — safe to proceed
    return RoutingResult(
        deadline_rule_keys=DOC_TYPE_TO_DEADLINE_RULES.get(doc_type, []),
        suggested_form_tags=DOC_TYPE_TO_FORM_TAGS.get(doc_type, []),
        escalate=False,
        escalation_reason=None,
        requires_human_review=False,
        review_reason=None,
        safe_to_auto_compute=bool(DOC_TYPE_TO_DEADLINE_RULES.get(doc_type)),
    )
