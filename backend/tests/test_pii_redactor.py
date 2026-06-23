"""
Tests for PII redaction (Phase 1 — PII minimization).

Covers: SSN detection, DOB detection, financial account numbers,
Florida driver licenses, and edge cases (no false positives on
dates that are not DOBs, no redaction of empty text).
"""

import pytest
from src.ingestion.pii_redactor import PIIRedactor, redact_pii


class TestPIIRedactor:
    """Unit tests for the PIIRedactor class."""

    def setup_method(self):
        self.redactor = PIIRedactor()

    # ── SSN tests ──────────────────────────────────────────────

    def test_redacts_labeled_ssn(self):
        text = "Petitioner SSN: 123-45-6789 filed this action."
        result = self.redactor.redact(text)
        assert "[REDACTED:ssn]" in result["redacted_text"]
        assert "123-45-6789" not in result["redacted_text"]
        assert result["count"] >= 1
        findings = [f for f in result["findings"] if f["type"] == "ssn"]
        assert len(findings) >= 1

    def test_redacts_bare_ssn(self):
        text = "The taxpayer identification 987-65-4321 must be included."
        result = self.redactor.redact(text)
        assert "[REDACTED:ssn]" in result["redacted_text"]
        assert "987-65-4321" not in result["redacted_text"]

    def test_does_not_redact_non_ssn_nine_digit(self):
        """A 9-digit number without SSN context or hyphens should not be redacted."""
        text = "Case Number: 2024-CF-001234. Amount: $5,000.00."
        result = self.redactor.redact(text)
        assert result["count"] == 0  # no SSN pattern matches

    def test_ssn_variations(self):
        text = "Social Security Number: 111-22-3333 and SS #: 444-55-6666"
        result = self.redactor.redact(text)
        assert result["count"] >= 2
        assert "111-22-3333" not in result["redacted_text"]
        assert "444-55-6666" not in result["redacted_text"]

    # ── DOB tests ──────────────────────────────────────────────

    def test_redacts_labeled_dob_slash_format(self):
        text = "Respondent DOB: 01/15/1985, resides in Miami-Dade County."
        result = self.redactor.redact(text)
        assert "[REDACTED:date_of_birth]" in result["redacted_text"]
        assert "01/15/1985" not in result["redacted_text"]

    def test_redacts_labeled_dob_long_format(self):
        text = "Date of Birth: January 15, 1985. Place of birth: Tampa."
        result = self.redactor.redact(text)
        assert "[REDACTED:date_of_birth]" in result["redacted_text"]
        assert "January 15, 1985" not in result["redacted_text"]

    def test_redacts_context_dob(self):
        text = "The child was born on 03/22/2019 at Memorial Hospital."
        result = self.redactor.redact(text)
        assert "[REDACTED:date_of_birth]" in result["redacted_text"]
        assert "03/22/2019" not in result["redacted_text"]

    def test_does_not_redact_court_dates(self):
        """Court filing dates and hearing dates should NOT be redacted."""
        text = (
            "Filed on 05/15/2024 in the Circuit Court. "
            "Hearing set for January 20, 2025 at 9:00 AM."
        )
        result = self.redactor.redact(text)
        # These are not labeled as DOB, so they should survive
        assert "05/15/2024" in result["redacted_text"]
        assert "January 20, 2025" in result["redacted_text"]

    # ── Financial account tests ────────────────────────────────

    def test_redacts_credit_card_labeled(self):
        text = "Payment by Credit Card Number: 4111-1111-1111-1111."
        result = self.redactor.redact(text)
        assert "[REDACTED:credit_card]" in result["redacted_text"]
        assert "4111-1111-1111-1111" not in result["redacted_text"]

    def test_redacts_bank_account_labeled(self):
        text = "Bank Account #: 1234567890 at First Florida Bank."
        result = self.redactor.redact(text)
        assert "[REDACTED:bank_account]" in result["redacted_text"]
        assert "1234567890" not in result["redacted_text"]

    def test_redacts_routing_number_labeled(self):
        text = "Routing Number: 063000047 for direct deposit."
        result = self.redactor.redact(text)
        assert "[REDACTED:routing_number]" in result["redacted_text"]
        assert "063000047" not in result["redacted_text"]

    # ── Florida DL tests ───────────────────────────────────────

    def test_redacts_fl_drivers_license(self):
        text = "Florida Driver License: A123456789012 issued 01/2022."
        result = self.redactor.redact(text)
        assert "[REDACTED:fl_drivers_license]" in result["redacted_text"]
        assert "A123456789012" not in result["redacted_text"]

    def test_redacts_fl_dl_variation(self):
        text = "FL DL #: B987654321098 exp. 06/2025."
        result = self.redactor.redact(text)
        assert "[REDACTED:fl_drivers_license]" in result["redacted_text"]
        assert "B987654321098" not in result["redacted_text"]

    # ── Edge cases ─────────────────────────────────────────────

    def test_empty_text(self):
        result = self.redactor.redact("")
        assert result["count"] == 0
        assert result["redacted_text"] == ""

    def test_no_pii_text(self):
        text = "This document contains no personally identifiable information."
        result = self.redactor.redact(text)
        assert result["count"] == 0
        assert result["redacted_text"] == text

    def test_multiple_pii_types(self):
        text = (
            "Petitioner SSN: 123-45-6789, DOB: 01/15/1985. "
            "Bank Account #: 9876543210. Florida DL: C555555555555."
        )
        result = self.redactor.redact(text)
        assert result["count"] >= 4
        # Verify no PII leaks
        assert "123-45-6789" not in result["redacted_text"]
        assert "01/15/1985" not in result["redacted_text"]
        assert "9876543210" not in result["redacted_text"]
        assert "C555555555555" not in result["redacted_text"]
        # Verify redaction markers present
        assert "[REDACTED:ssn]" in result["redacted_text"]
        assert "[REDACTED:date_of_birth]" in result["redacted_text"]
        assert "[REDACTED:bank_account]" in result["redacted_text"]

    def test_findings_have_required_fields(self):
        text = "SSN: 111-22-3333"
        result = self.redactor.redact(text)
        for f in result["findings"]:
            assert "type" in f
            assert "value_hash" in f
            assert "span" in f
            assert "matched_by" in f
            assert len(f["value_hash"]) == 16  # sha256 truncated

    def test_no_false_positive_on_partial_match(self):
        """Numbers that look similar but aren't PII should be left alone."""
        text = "Phone: 555-123-4567. Fax: 555-987-6543."
        result = self.redactor.redact(text)
        # Phone numbers have different format (xxx-xxx-xxxx vs xxx-xx-xxxx)
        assert "555-123-4567" in result["redacted_text"]
        assert "555-987-6543" in result["redacted_text"]

    def test_convenience_function(self):
        text = "SSN: 111-22-3333"
        result = redact_pii(text)
        assert result["count"] == 1
        assert "[REDACTED:ssn]" in result["redacted_text"]


class TestPIIRedactorRealWorld:
    """Tests against realistic Florida court document snippets."""

    def setup_method(self):
        self.redactor = PIIRedactor()

    def test_fl_family_law_petition_header(self):
        """Realistic dissolution of marriage petition header."""
        text = (
            "IN THE CIRCUIT COURT OF THE ELEVENTH JUDICIAL CIRCUIT\n"
            "IN AND FOR MIAMI-DADE COUNTY, FLORIDA\n\n"
            "In re the Marriage of:\n"
            "JOHN DOE, Petitioner,\n"
            "SSN: 123-45-6789\n"
            "DOB: 01/15/1985\n"
            "and\n"
            "JANE DOE, Respondent,\n"
            "SSN: 987-65-4321\n"
            "DOB: March 22, 1987\n"
        )
        result = self.redactor.redact(text)
        assert result["count"] >= 4
        assert "123-45-6789" not in result["redacted_text"]
        assert "987-65-4321" not in result["redacted_text"]
        assert "01/15/1985" not in result["redacted_text"]
        assert "March 22, 1987" not in result["redacted_text"]
        # Court name and county should survive
        assert "MIAMI-DADE COUNTY" in result["redacted_text"]
        assert "ELEVENTH JUDICIAL CIRCUIT" in result["redacted_text"]

    def test_fl_financial_affidavit_fragment(self):
        """Realistic financial affidavit snippet."""
        text = (
            "FAMILY LAW FINANCIAL AFFIDAVIT\n\n"
            "Employer: Acme Corp\n"
            "Bank Account #: 1234567890\n"
            "Routing #: 063000047\n"
            "Credit Card #: 4111-1111-1111-1111 (Visa)\n"
            "Monthly income: $4,500.00\n"
        )
        result = self.redactor.redact(text)
        assert "[REDACTED:bank_account]" in result["redacted_text"]
        assert "[REDACTED:routing_number]" in result["redacted_text"]
        assert "[REDACTED:credit_card]" in result["redacted_text"]
        # Non-PII info survives
        assert "Acme Corp" in result["redacted_text"]
        assert "$4,500.00" in result["redacted_text"]
