"""
PII redaction pass for retained document_text.

Runs after extraction and cleaning, before the text is stored.
Targets: SSNs, full dates of birth, and financial account numbers.

Uses regex (no external services) — deterministic and auditable.
Every redaction produces a structured log entry for traceability.
"""

import hashlib
import re
from typing import Dict, List


class PIIRedactor:
    """Deterministic PII redaction for Florida court documents.

    Removes SSNs, full dates of birth, and financial account numbers
    from retained document_text. Uses conservative regex patterns
    with context anchoring to minimize false positives.

    Legal documents contain structured PII (petition headers, financial
    affidavits, child support worksheets). The patterns below target the
    specific formats found in Florida family-law and civil forms.
    """

    # ── SSN patterns ──────────────────────────────────────────────
    # Standard SSN: 123-45-6789 with word boundaries
    SSN_RE = re.compile(
        r'(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)',
    )
    # SSN with label context: "SSN:", "Social Security:", "SS #:"
    SSN_LABELED_RE = re.compile(
        r'(?:SSN|Social\s*Security|SS)\s*(?:#|Number|No\.?)?\s*:?\s*'
        r'(?P<ssn>\d{3}-\d{2}-\d{4})',
        re.IGNORECASE,
    )

    # ── Date of birth patterns ────────────────────────────────────
    # Labeled DOB: "DOB: 01/15/1985", "Date of Birth: January 15, 1985"
    DOB_LABELED_RE = re.compile(
        r'(?:DOB|Date\s*of\s*Birth|Birth\s*Date)\s*:?\s*'
        r'(?P<dob>'
        r'\d{1,2}/\d{1,2}/\d{2,4}'                # 01/15/1985
        r'|'
        r'(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'  # January 15, 1985
        r')',
        re.IGNORECASE,
    )
    # Age-qualified DOB context: "was born on", "date of birth is"
    DOB_CONTEXT_RE = re.compile(
        r'(?:born\s+on|date\s+of\s+birth\s+(?:is\s+)?)\s*'
        r'(?P<dob>'
        r'\d{1,2}/\d{1,2}/\d{2,4}'
        r'|'
        r'(?:January|February|March|April|May|June|'
        r'July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        r')',
        re.IGNORECASE,
    )

    # ── Financial account patterns ─────────────────────────────────
    # Credit card numbers (13-19 digits, major issuers)
    # We only match if preceded by a label to avoid false positives
    CC_LABELED_RE = re.compile(
        r'(?:Credit\s*Card|CC|Card\s*Number|Payment\s*Card)\s*(?:#|Number|No\.?)?\s*:?\s*'
        r'(?P<cc>\d[\d\s-]{12,22}\d)',
        re.IGNORECASE,
    )
    # Bank account numbers (labeled: "Account #:", "Acct:", "Bank Account:")
    ACCOUNT_LABELED_RE = re.compile(
        r'(?:Account|Acct|Bank\s*Account|Routing)\s*(?:#|Number|No\.?)?\s*:?\s*'
        r'(?P<acct>\d[\d\s-]{6,24}\d)',
        re.IGNORECASE,
    )
    # Routing numbers (9 digits, labeled)
    ROUTING_LABELED_RE = re.compile(
        r'(?:Routing|ABA|Transit)\s*(?:#|Number|No\.?)?\s*:?\s*'
        r'(?P<routing>\d{9})',
        re.IGNORECASE,
    )

    # ── Driver license / state ID ──────────────────────────────────
    # Florida DL: 1 letter + 12 digits
    FL_DL_RE = re.compile(
        r'(?:Driver\'?s?\s*License|DL|FL\s*DL|Florida\s*DL|State\s*ID)\s*(?:#|Number|No\.?)?\s*:?\s*'
        r'(?P<dl>[A-Za-z]\d{12})',
        re.IGNORECASE,
    )

    def redact(self, text: str) -> Dict:
        """Run all redaction passes and return redacted text + audit log.

        Returns:
            dict with keys:
                redacted_text: str — text with PII replaced by [REDACTED:type]
                findings: list — structured log of each redaction
                count: int — total redactions performed
        """
        findings: List[Dict] = []
        redacted = text

        # Order matters: labeled patterns first (more specific), then bare SSN

        # 1. Labeled SSNs
        for match in self.SSN_LABELED_RE.finditer(text):
            ssn = match.group('ssn')
            findings.append({
                'type': 'ssn',
                'value_hash': self._hash_value(ssn),
                'span': match.span(),
                'matched_by': 'ssn_labeled',
            })

        # 2. Labeled DOBs
        for match in self.DOB_LABELED_RE.finditer(text):
            dob = match.group('dob')
            findings.append({
                'type': 'date_of_birth',
                'value_hash': self._hash_value(dob),
                'span': match.span(),
                'matched_by': 'dob_labeled',
            })

        # 3. Context DOBs
        for match in self.DOB_CONTEXT_RE.finditer(text):
            dob = match.group('dob')
            # Avoid double-counting spans already caught by labeled
            if not any(f['span'][0] <= match.start() and f['span'][1] >= match.end()
                       and f['type'] == 'date_of_birth'
                       for f in findings):
                findings.append({
                    'type': 'date_of_birth',
                    'value_hash': self._hash_value(dob),
                    'span': match.span(),
                    'matched_by': 'dob_context',
                })

        # 4. Bare SSNs (only those not already caught by labeled)
        for match in self.SSN_RE.finditer(text):
            if not any(f['span'][0] <= match.start() and f['span'][1] >= match.end()
                       and f['type'] == 'ssn'
                       for f in findings):
                findings.append({
                    'type': 'ssn',
                    'value_hash': self._hash_value(match.group()),
                    'span': match.span(),
                    'matched_by': 'ssn_bare',
                })

        # 5. Credit card numbers
        for match in self.CC_LABELED_RE.finditer(text):
            findings.append({
                'type': 'credit_card',
                'value_hash': self._hash_value(match.group('cc')),
                'span': match.span(),
                'matched_by': 'cc_labeled',
            })

        # 6. Bank account numbers
        for match in self.ACCOUNT_LABELED_RE.finditer(text):
            findings.append({
                'type': 'bank_account',
                'value_hash': self._hash_value(match.group('acct')),
                'span': match.span(),
                'matched_by': 'account_labeled',
            })

        # 7. Routing numbers
        for match in self.ROUTING_LABELED_RE.finditer(text):
            findings.append({
                'type': 'routing_number',
                'value_hash': self._hash_value(match.group('routing')),
                'span': match.span(),
                'matched_by': 'routing_labeled',
            })

        # 8. Florida driver licenses
        for match in self.FL_DL_RE.finditer(text):
            findings.append({
                'type': 'fl_drivers_license',
                'value_hash': self._hash_value(match.group('dl')),
                'span': match.span(),
                'matched_by': 'fl_dl',
            })

        # Apply redactions in reverse span order so offsets stay valid
        findings.sort(key=lambda f: f['span'][0], reverse=True)
        for f in findings:
            start, end = f['span']
            replacement = f'[REDACTED:{f["type"]}]'
            redacted = redacted[:start] + replacement + redacted[end:]

        return {
            'redacted_text': redacted,
            'findings': findings,
            'count': len(findings),
        }

    @staticmethod
    def _hash_value(value: str) -> str:
        """Non-reversible hash for audit trail (sha256 truncated)."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]


# Module-level singleton
_redactor = PIIRedactor()


def redact_pii(text: str) -> Dict:
    """Convenience function: redact PII from document text.

    Returns same dict as PIIRedactor.redact().
    """
    return _redactor.redact(text)
