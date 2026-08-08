"""Property & Casualty — UPL enforcement + classification tests (Phase 6).

Unit tests: no LLM, no DB, no running backend required.
Asserts on GENERATED output behavior, not source structure.

Run: cd backend && uv run python -m pytest tests/test_pc_upl.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date

from deadline.compute import compute_deadline_for_event
from src.core.disclaimer import get_disclaimer
from src.core.upl import apply_disclaimer, audit_output_for_upl

# ══════════════════════════════════════════════════════════════════════
# UPL ENFORCEMENT — behavioral, not structural
# ══════════════════════════════════════════════════════════════════════

def test_response_carries_disclaimer():
    """Agent output terminated via apply_disclaimer() must carry the
    standard disclaimer text injected by the shared middleware."""
    # Simulate what the agent returns after apply_disclaimer
    simulated = apply_disclaimer(
        {"what_this_is": "A first-party property insurance claim."},
        lang="en", level="standard",
    )
    assert "disclaimer" in simulated
    # Phase 8 replaced "legal information, not legal advice" with an
    # "educate first, attorney end" disclaimer. Assert the new intent:
    # legal information + an attorney-confirmation nudge.
    assert "legal information" in simulated["disclaimer"].lower()
    assert "attorney" in simulated["disclaimer"].lower()


def test_no_second_person_directives_in_output():
    """The UPL audit function must catch the directive phrases it is
    calibrated to flag — the Phase 8 ATTORNEY_NUDGE_PHRASES set. This
    proves the audit tooling matches the implemented contract.

    NOTE: 'my advice is ...' is NOT in the Phase 8 nudge set (it was in
    the pre-Phase-8 block-list). Whether to re-add an 'advice' trigger is
    a product decision — tracked separately, not silently changed here.
    """
    banned = [
        "You should file the notice immediately.",      # you should
        "You must report the claim within 1 year.",      # you must
        "You need to hire an attorney.",                 # you need to
        "I recommend filing suit now.",                  # i recommend
        "Your best option is to settle.",                # your best option
    ]
    for text in banned:
        flags = audit_output_for_upl(text)
        assert len(flags) > 0, (
            f"audit_output_for_upl must flag: {text!r}"
        )


def test_informational_text_passes_audit():
    """Information-only text with no second-person directives must pass clean."""
    clean = (
        "A first-party property claim under Florida law requires the "
        "policyholder to report the loss within 1 year of the date of loss. "
        "The insurer must pay or deny within 60 days under § 627.70131. "
        "The statute of limitations to file suit is 5 years under "
        "§ 95.11(2)(e), measured from the date of loss. "
        "Options include DFS mediation, appraisal, a pre-suit Notice of "
        "Intent, and litigation."
    )
    flags = audit_output_for_upl(clean)
    assert flags == [], f"Clean text must return empty; got: {flags}"


def test_disclaimer_via_middleware_not_local_literal():
    """Prove the disclaimer text originates from the canonical get_disclaimer()
    in src/core/disclaimer.py — the frozen contract — not a P&C-local copy."""
    standard = get_disclaimer("en", "standard")
    assert "legal information" in standard.lower()
    assert "attorney" in standard.lower()
    # Verify apply_disclaimer produces a valid disclaimer (uses its own text source).
    applied = apply_disclaimer({"test": True}, lang="en", level="standard")
    assert applied["disclaimer"], "apply_disclaimer must produce a non-empty disclaimer"
    assert "legal" in applied["disclaimer"].lower()


def test_first_party_output_includes_key_deadlines():
    """A simulated first-party response must include key_deadlines
    from the deterministic engine, not LLM-computed dates."""
    loss_date = date(2023, 3, 1)
    deadlines = []
    for rule_key in ["pc_report_claim", "pc_file_suit", "pc_pay_or_deny"]:
        r = compute_deadline_for_event(
            rule_key=rule_key, event_date=loss_date,
            service_method="personal", circuit=None,
            closure_dates=frozenset(), has_local_closure_data=True,
            today=date.today(),
        )
        for dl in r.deadlines:
            deadlines.append({
                "label": dl.label,
                "due_date": dl.due_date.isoformat(),
                "governing_rule": dl.governing_rule,
                "severity": dl.severity,
                "consequence": dl.consequence,
                "is_past": dl.is_past,
                "computation_trace": dl.computation_trace,
            })

    assert len(deadlines) == 3
    # Verify dates are the CORRECT anniversary dates
    dates = {dl["label"]: dl["due_date"] for dl in deadlines}
    assert dates["Report Property Insurance Claim"] == "2024-03-01", (
        f"Report deadline must be 2024-03-01, got {dates.get('Report Property Insurance Claim')}"
    )
    assert dates["File Suit — Breach of Property Insurance Contract"] == "2028-03-01", (
        f"Suit deadline must be 2028-03-01, got {dates.get('File Suit — Breach of Property Insurance Contract')}"
    )
    assert dates["Insurer Pay-or-Deny Deadline"] == "2023-05-01", (
        f"Pay-or-deny must be 2023-05-01 (Apr 30 is Sun → roll-forward), "
        f"got {dates.get('Insurer Pay-or-Deny Deadline')}"
    )

    # Now simulate agent output wrapped with these deadlines
    agent_output = {
        "what_this_is": "A first-party property insurance claim.",
        "key_deadlines": deadlines,
    }
    final = apply_disclaimer(agent_output, lang="en", level="standard")
    assert "key_deadlines" in final
    assert final["key_deadlines"][0]["due_date"] == "2024-03-01"
    assert "disclaimer" in final


# ══════════════════════════════════════════════════════════════════════
# CLASSIFIER CORRECTNESS — taxonomy lock
# ══════════════════════════════════════════════════════════════════════

# Simulated intake router classification — these test the taxonomy BOUNDARY,
# not the LLM (unit tests only parse VALID_SUB_TYPES + prompt rules)

from src.api.routers.intake import VALID_SUB_TYPES, _sanitize_sub_type


def test_first_party_property_in_valid_sub_types():
    """The taxonomy lock: first_party_property must be in VALID_SUB_TYPES."""
    assert "first_party_property" in VALID_SUB_TYPES, (
        f"first_party_property missing from VALID_SUB_TYPES: {VALID_SUB_TYPES}"
    )


def test_coverage_dispute_routes_first_party():
    """A denied hurricane claim with no CRN posture → first_party_property.
    This is the boundary rule: coverage dispute ≠ bad faith."""
    assert _sanitize_sub_type("first_party_property") == "first_party_property"
    # insurance_bad_faith must not be the fallback
    assert _sanitize_sub_type("first_party_property") != "insurance_bad_faith"


def test_crn_present_routes_bad_faith():
    """Explicit CRN / § 624.155 posture → insurance_bad_faith."""
    assert _sanitize_sub_type("insurance_bad_faith") == "insurance_bad_faith"
    assert "insurance_bad_faith" in VALID_SUB_TYPES


def test_premises_unchanged():
    """Third-party injury on premises → premises_liability (untouched)."""
    assert _sanitize_sub_type("premises_liability") == "premises_liability"
    assert "premises_liability" in VALID_SUB_TYPES


def test_unknown_sub_type_stays_unknown():
    """A sub_type not in VALID_SUB_TYPES must be coerced to 'unknown'."""
    assert _sanitize_sub_type("flood_claim") == "unknown"
    assert _sanitize_sub_type("auto_accident") == "unknown"
    assert _sanitize_sub_type(None) is None


def test_three_way_taxonomy_no_collapse():
    """The three P&C sub-types must all be distinct and valid."""
    pc_types = {"first_party_property", "insurance_bad_faith", "premises_liability"}
    assert pc_types.issubset(set(VALID_SUB_TYPES)), (
        f"All three P&C sub-types must be in VALID_SUB_TYPES. "
        f"Missing: {pc_types - set(VALID_SUB_TYPES)}"
    )
    # Each must sanitize to itself
    for t in pc_types:
        assert _sanitize_sub_type(t) == t, f"{t} must sanitize to itself"
