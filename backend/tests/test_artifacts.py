"""I-7 — artifact generator tests (deterministic, no IO beyond weasyprint)."""

import re
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone

import pytest

from src.agents import artifacts
from src.agents.pc_citations import PC_CURATED_CITATIONS
from src.core.citation_resolver import resolve_citation

FULL_DETAILS = {
    "insured_name": "Jane Policyholder",
    "insured_address": "123 First Street, Miami, FL 33101",
    "insurer_name": "Example Insurance Co.",
    "claim_number": "CLM-2026-0042",
    "policy_number": "POL-98765",
    "adjuster_name": "Alex Adjuster",
    "property_address": "123 First Street, Miami, FL 33101",
    "fire_report_number": "FR-2026-118",
    "mortgage_company": "Sample Mortgage",
    "phone_number": "(305) 555-0100",
    "date_of_loss": "2026-08-01",
}

CLAIM = {
    "id": "11111111-1111-1111-1111-111111111111",
    "peril": "fire",
    "date_of_loss": "2026-08-01",
    "created_at": "2026-08-01T10:00:00+00:00",
}

EVENTS = [
    {"trigger_name": "date_of_loss", "occurred_at": "2026-08-01T09:00:00+00:00"},
    {"trigger_name": "claim_number_received", "occurred_at": "2026-08-02T09:00:00+00:00",
     "note": "Called insurer, spoke to intake."},
]

DEADLINES = [
    {"label": "Insurer acknowledges claim", "due_date": "2026-08-08",
     "governing_rule": "Fla. Stat. § 627.70131"},
    {"label": "File suit deadline", "due_date": "2031-08-01",
     "governing_rule": "Fla. Stat. § 95.11(2)(e)"},
]


def test_catalog_has_both_batches():
    ids = set(artifacts.ARTIFACT_CATALOG)
    batch_a = {"claim_log", "policy_request_letter", "vacancy_notice",
               "work_auth_rider", "packout_demand", "contents_inventory_csv",
               "contents_inventory_pdf"}
    batch_b = {"depreciation_challenge", "supplement_cover", "demand_letter",
               "dfs_mediation_prefill", "deadline_calendar_ics"}
    assert batch_a <= ids
    assert batch_b <= ids


def test_unknown_artifact_raises():
    with pytest.raises(KeyError):
        artifacts.build_artifact("not_a_thing", CLAIM, EVENTS, DEADLINES, FULL_DETAILS)


def test_every_artifact_builds_with_full_details():
    for artifact_id in artifacts.ARTIFACT_CATALOG:
        payload, mime, filename = artifacts.build_artifact(
            artifact_id, CLAIM, EVENTS, DEADLINES, FULL_DETAILS)
        assert len(payload) > 0, artifact_id
        assert filename.endswith(artifacts.ARTIFACT_CATALOG[artifact_id]["ext"])


def test_pdf_artifacts_are_real_pdfs():
    for artifact_id, meta in artifacts.ARTIFACT_CATALOG.items():
        if meta["ext"] != "pdf":
            continue
        payload, _, _ = artifacts.build_artifact(artifact_id, CLAIM, EVENTS, DEADLINES, FULL_DETAILS)
        assert payload[:5] == b"%PDF-", artifact_id


def test_missing_fields_listed_and_placeholders_rendered():
    missing = artifacts.missing_fields({})
    assert "insured_name" in missing
    html_str = artifacts._policy_request_html({})
    assert "[insurance company name]" in html_str
    assert "[your name]" in html_str
    assert "<b>Example Insurance Co.</b>" not in html_str


def test_letter_citations_resolve_against_curated_set():
    """Every citation rendered in any letter body must resolve against the
    owned P&C curated set — the same gate the content loader enforces."""
    letter_builders = [
        artifacts._policy_request_html,
        artifacts._work_auth_rider_html,
        artifacts._supplement_cover_html,
        artifacts._demand_letter_html,
        artifacts._dfs_mediation_prefill_html,
    ]
    cite_re = re.compile(r"Fla\.\s*Stat\.\s*&sect;\s*([0-9]+(?:\.[0-9]+)?)")
    found: list[str] = []
    for builder in letter_builders:
        html_str = builder(FULL_DETAILS)
        found.extend(cite_re.findall(html_str))
    assert found, "expected at least one citation across the letters"
    for section in found:
        citation = f"Fla. Stat. § {section}"
        assert resolve_citation(citation, PC_CURATED_CITATIONS) is not None, citation


def test_claim_log_newest_first():
    events = [
        {"trigger_name": "claim_number_received", "occurred_at": "2026-08-02T09:00:00+00:00"},
        {"trigger_name": "payment_received", "occurred_at": "2026-08-20T09:00:00+00:00"},
    ]
    html_str = artifacts._claim_log_html(CLAIM, events, FULL_DETAILS)
    assert html_str.index("payment_received") < html_str.index("claim_number_received")


def test_claim_log_empty_state():
    html_str = artifacts._claim_log_html(CLAIM, [], FULL_DETAILS)
    assert "No events recorded yet" in html_str


def test_inventory_csv_header_order():
    csv_bytes = artifacts._contents_inventory_csv(FULL_DETAILS)
    header = csv_bytes.decode("utf-8").splitlines()[0]
    assert header == ",".join(artifacts._INVENTORY_COLUMNS)


def test_ics_structure_and_escaping():
    deadlines = [
        {"label": "Insurer acknowledges claim — see policy, also letters",
         "due_date": "2026-08-08", "governing_rule": "Fla. Stat. § 627.70131"},
    ]
    ics = artifacts._deadline_calendar_ics(CLAIM, deadlines).decode("utf-8")
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" in ics
    assert "DTSTART;VALUE=DATE:20260808" in ics
    assert r"see policy\, also letters" in ics  # comma escaped


def test_ics_skips_deadlines_without_dates():
    ics = artifacts._deadline_calendar_ics(CLAIM, [{"label": "x", "due_date": ""}]).decode("utf-8")
    assert "BEGIN:VEVENT" not in ics


def test_draft_note_on_every_letter():
    for builder in [artifacts._policy_request_html, artifacts._vacancy_notice_html,
                    artifacts._packout_demand_html, artifacts._demand_letter_html]:
        html_str = builder(FULL_DETAILS)
        assert "draft document prepared by the policyholder" in html_str


def test_detail_values_rendered_not_placeholder():
    html_str = artifacts._policy_request_html(FULL_DETAILS)
    assert "Example Insurance Co." in html_str
    assert "CLM-2026-0042" in html_str
    assert "POL-98765" in html_str
    assert "Jane Policyholder" in html_str
