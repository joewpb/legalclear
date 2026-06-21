"""Scanner Agent — Phase 21.

Source: phases/source/PHASE_21_police_report.md

Flags procedural and factual discrepancies in a police report (plus any
supplementary witness/dispatch/body-cam transcripts). This is document
analysis — NOT legal advice. Output is a flat list of structured
findings the user can take to a defense attorney.

Universal rules honored:
  - `cache_control: ephemeral` on the system prompt
  - Markdown fences stripped before `json.loads()`
  - Single JSON-parse retry before falling back to empty findings
  - Typed dict return shape
  - Does NOT modify the existing classifier / risk_scanner / explainer

Failure policy: ANY exception (missing API key, network failure, malformed
JSON after retry, no PDF text) yields `{"findings": [], "meta": {...}}`
rather than a 500. The router relies on this to keep the upload endpoint
returning 200 even when extraction or analysis can't run.
"""
from __future__ import annotations

import json
import logging
import traceback
from typing import Any

from anthropic import Anthropic

from src.agents.case_context import empty_case_context
from src.agents.police_report_v2 import compute_risk_score
from src.core.config import settings

logger = logging.getLogger(__name__)

SCANNER_PROMPT = """You are a document analyzer reviewing a police report and any supplementary documents the user uploaded. Your job is to flag inconsistencies and procedural issues a defense attorney would want to know about.

You are NOT giving legal advice. You are NOT recommending a defense strategy. You are pointing out things to ask an attorney about.

Categories to scan:
1. Temporal inconsistencies — timestamps that don't align across documents
2. Spatial inconsistencies — locations described differently
3. Procedural issues — missing Miranda reference in custodial situations, no articulated probable cause for searches, no consent documentation
4. Officer account variance — if multiple officers describe the same event, where do they diverge?
5. Missing required elements — witness names withheld, evidence chain gaps, no badge numbers
6. Internal contradictions within a single document

Output ONLY a JSON array. Each finding:
{
  "category": "Temporal",
  "severity": "high|medium|low",
  "page_reference": "p.3, paragraph 4",
  "finding": "Plain-English description of the inconsistency",
  "ask_your_attorney_about": "What to raise with your lawyer"
}

Do not invent findings. If a category has no issues, omit it. If the documents are too short or lack context to analyze, return an empty array.
"""

CASE_CONTEXT_PROMPT = """You are analyzing a police report and any supplementary documents.

Extract ONLY stated facts. Do NOT assess whether any action was lawful or unlawful.
Do NOT draw legal conclusions. Quote statute numbers verbatim if they appear in the
document; never generate or infer them. Leave the "derived" group with all null/empty
defaults — do not populate it.

Return a single JSON object with this exact structure:
{
  "routing": {
    "userRole": "<one of: suspect | personOfInterest | victim | complainant | witness | involvedDriver | citationHolder | juvenile | other | unclear>",
    "reportType": "<one of: arrestReport | incidentReport | crashReport | citation | juvenileReport | unknown>",
    "routingConfidence": <float 0-1>
  },
  "document": {
    "agency": "<string or null>",
    "reportNumber": "<string or null>",
    "reportDate": "<string or null>",
    "extractionConfidence": <float 0-1>
  },
  "incident": {
    "incidentDateTime": "<string or null>",
    "incidentLocation": "<string or null>",
    "incidentType": "<string or null>",
    "charges": ["<charge string>"],
    "statuteReferences": ["<verbatim statute citation from document>"]
  },
  "rightsEvents": {
    "arrestMade": <boolean>,
    "searchOccurred": <boolean>,
    "searchContext": "<string describing what was searched and the stated basis, or null>",
    "mirandaMentioned": <boolean>,
    "custodialIndicators": ["<indicator string>"],
    "statementsAttributed": <boolean>
  },
  "people": {
    "officers": [{"name": "<string or null>", "badge": "<string or null>", "role": "<string or null>"}],
    "otherPartiesCount": <integer>
  },
  "discrepancies": [
    {
      "type": "<one of: temporal | spatial | missingMiranda | probableCauseGap | inconsistentAccounts>",
      "detail": "<string>",
      "sourceLocation": "<string or null>",
      "confidence": <float 0-1>
    }
  ],
  "sensitivity": {
    "domesticViolence": <boolean>,
    "sexualOffense": <boolean>,
    "juvenileInvolved": <boolean>
  },
  "derived": {
    "timelineStage": null,
    "deadlines": [],
    "questionsForCounsel": [],
    "collateralConsequenceFlags": []
  }
}

Role detection:
- "suspect" / "personOfInterest": named as arrestee, defendant, or suspect
- "victim" / "complainant": identified as the person harmed or who made the complaint
- "witness": present only as an observer
- "involvedDriver": driver in a crash report who is not a suspect
- "citationHolder": received a traffic citation without arrest
- "juvenile": document identifies the subject as a minor
- "other": present but does not fit categories above
- "unclear": role cannot be determined from the document — PREFER this over a
  confident wrong answer; set routingConfidence below 0.5

For unknown fields use: null (strings), false (booleans), [] (arrays), 0 (numbers).
"""

# Model: source spec calls for claude-sonnet-4-6 (same family confirmed
# for classifier/explainer per Phase 03/04 ledger entries).
_MODEL = "claude-sonnet-4-6"


def _strip_fences(raw: str) -> str:
    """Strip ```json ... ``` fences if present (universal rule)."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 2:
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
    return raw.strip()


def _parse_findings(raw: str) -> list[dict[str, Any]]:
    """Parse the model's response into a findings list. Retry once on
    JSONDecodeError (AGENTS.md universal rule)."""
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # One retry: try to recover the largest JSON-looking substring.
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return []
        else:
            return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict)]


async def scan_documents(extracted_texts: list[dict]) -> dict:
    """Run the Scanner Agent against a list of extracted-document dicts.

    Args:
        extracted_texts: list of {"filename": str, "text": str} dicts
            produced by the Phase 02 ingestion pipeline.

    Returns:
        {"findings": [...], "meta": {"documents_analyzed": N, ...}}
    """
    n_docs = len(extracted_texts)
    meta: dict[str, Any] = {"documents_analyzed": n_docs}

    # If we have nothing to analyze, skip the API call entirely.
    if n_docs == 0 or not any(d.get("text") for d in extracted_texts):
        meta["note"] = "no document text extracted"
        return {
            "findings": [],
            "meta": meta,
            "risk_analysis": compute_risk_score([]),
        }

    combined = "\n\n---\n\n".join(
        f"[FILE: {d.get('filename', 'unknown')}]\n{(d.get('text') or '')[:30000]}"
        for d in extracted_texts
    )

    try:
        client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=2,
            timeout=120.0,
        )
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": SCANNER_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": combined}],
        )
        raw = msg.content[0].text if msg.content else ""
        findings = _parse_findings(raw)

        # Compute deterministic risk score from LLM-classified severities.
        # The scanner uses "finding" for description; map to the field
        # name compute_risk_score expects.
        risk_input = [
            {**f, "description": f.get("finding", "")} for f in findings
        ]
        risk_analysis = compute_risk_score(risk_input)

        return {
            "findings": findings,
            "meta": meta,
            "risk_analysis": risk_analysis,
        }
    except Exception as e:  # noqa: BLE001 — fail-soft is the contract
        logger.warning(
            "Scanner agent failed (%s); returning empty findings.\n%s",
            type(e).__name__,
            traceback.format_exc(),
        )
        meta["error"] = type(e).__name__
        return {
            "findings": [],
            "meta": meta,
            "risk_analysis": compute_risk_score([]),
        }


def _parse_case_context_obj(raw: str) -> dict | None:
    """Parse the model's case-context response into a dict. Retry once."""
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
        else:
            return None
    if not isinstance(data, dict):
        return None
    return data


async def extract_case_context(extracted_texts: list[dict]) -> dict:
    """Run the CaseContext extraction prompt against the same document list.

    Returns a CaseContext-shaped dict on success; falls back to
    empty_case_context() on ANY exception, missing API key, empty text,
    or unparseable JSON — never raises, never returns 500.
    """
    if not extracted_texts or not any(d.get("text") for d in extracted_texts):
        return empty_case_context()

    combined = "\n\n---\n\n".join(
        f"[FILE: {d.get('filename', 'unknown')}]\n{(d.get('text') or '')[:30000]}"
        for d in extracted_texts
    )

    try:
        client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=2,
            timeout=120.0,
        )
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": CASE_CONTEXT_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": combined}],
        )
        raw = msg.content[0].text if msg.content else ""
        parsed = _parse_case_context_obj(raw)
        return parsed if parsed is not None else empty_case_context()
    except Exception as e:  # noqa: BLE001 — fail-soft contract
        logger.warning(
            "CaseContext extraction failed (%s); returning empty context.\n%s",
            type(e).__name__,
            traceback.format_exc(),
        )
        return empty_case_context()
