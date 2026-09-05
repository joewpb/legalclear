"""Phase C2 — per-citation Haiku adjudication (deterministic shell, LLM verdict).

For every citation the C1 floor verified, ONE Haiku call receives the
official statute text, the claim context (the window around the citation in
the analysis), and the report situation. Verdict ∈ SUPPORTED | WRONG_SCOPE |
CONTRADICTS.

- SUPPORTED → the citation stays; the log entry gains the adjudication and
  the plain-English explanation.
- WRONG_SCOPE / CONTRADICTS → deterministic exact-text scrub + note
  (citation_validation.scrub_exact_citation). The LLM picks the canned
  action; deterministic code applies it — the C1 floor always wins.
- LLM transport failure or unrecoverable JSON → the citation STAYS, marked
  ``unavailable`` (a verified citation is never stripped on the strength of
  a failed call).

Never raises. The caller wraps it in try/except so adjudication failure can
never break the analysis.
"""

from __future__ import annotations

import copy
import json
import logging

from src.core.config import settings
from src.core.json_utils import strip_markdown_fences
from src.services.citation_validation import scrub_exact_citation

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_VERDICTS = frozenset({"SUPPORTED", "WRONG_SCOPE", "CONTRADICTS"})

_SCOPE_NOTE = (
    "The analysis cited {cite} in a way the statute's text does not "
    "support, so the claim was removed."
)


def _situation(analysis: dict, limit: int = 500) -> str:
    parts: list[str] = []
    summary = analysis.get("incident_summary")
    if isinstance(summary, str) and summary.strip():
        parts.append(summary.strip())
    charges = [
        c.get("charge", "") for c in analysis.get("charges_explained") or []
        if isinstance(c, dict) and c.get("charge")
    ]
    if charges:
        parts.append("Charges: " + "; ".join(str(c) for c in charges[:3]))
    return (" ".join(parts))[:limit]


def _build_prompt(entry: dict, situation: str) -> str:
    return (
        "A Florida police-report analysis for a pro se user cites a "
        "statute. Decide whether the statute's actual text supports the "
        "claim the analysis makes in the given context.\n"
        f"CITATION: {entry.get('citation', '')}\n"
        f"STATUTE TITLE: {entry.get('title', '')}\n"
        f"STATUTE TEXT: {(entry.get('statute_text') or '')[:1200]}\n"
        f"CLAIM CONTEXT: {(entry.get('context') or '')[:500]}\n"
        f"USER SITUATION: {situation}\n"
        'Return ONLY a JSON object: {"verdict": "SUPPORTED" | '
        '"WRONG_SCOPE" | "CONTRADICTS", "explanation": "one plain-English '
        'sentence"}.\n'
        "- SUPPORTED = the statute text does what the claim says, in a "
        "context where the statute applies.\n"
        "- WRONG_SCOPE = the statute exists but governs a different context "
        "(e.g. court proceedings, not roadside conduct).\n"
        "- CONTRADICTS = the statute text says the opposite of the claim.\n"
    )


def _call_haiku(key: str, entry: dict, situation: str):
    """One Haiku HTTP call. Returns (verdict, explanation) or (None, None)."""
    import requests as _requests

    try:
        resp = _requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": _HAIKU_MODEL,
                "messages": [{
                    "role": "user",
                    "content": _build_prompt(entry, situation),
                }],
                "max_tokens": 200,
                "temperature": 0.0,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(
                "citation adjudication Haiku returned HTTP %s",
                resp.status_code,
            )
            return None, None
        raw = resp.json()["content"][0]["text"].strip()
    except Exception:
        logger.warning(
            "citation adjudication Haiku request failed; keeping citation",
            exc_info=True,
        )
        return None, None

    try:
        obj = json.loads(strip_markdown_fences(raw))
        verdict = str(obj.get("verdict", "")).strip().upper()
        if verdict not in _VERDICTS:
            logger.warning(
                "citation adjudication Haiku returned invalid verdict %r",
                obj.get("verdict"),
            )
            return None, None
        return verdict, str(obj.get("explanation", ""))
    except Exception:
        logger.warning(
            "citation adjudication Haiku JSON unrecoverable; keeping "
            "citation",
            exc_info=True,
        )
        return None, None


def adjudicate_verified_citations(
    analysis: dict,
    log: list[dict],
    language: str = "en",
) -> tuple[dict, list[dict]]:
    """Adjudicate every C1-verified citation; apply the canned action.

    Returns (scrubbed_analysis, enriched_log). Zero calls when there is no
    API key, no verified citation, or a verified citation lacks its
    statute text / claim context. Never raises for LLM problems.
    """
    key = settings.ANTHROPIC_API_KEY
    if not key or not isinstance(log, list):
        return analysis, log
    if not any(
        isinstance(e, dict)
        and e.get("status") == "verified"
        and e.get("context")
        and e.get("statute_text")
        for e in log
    ):
        return analysis, log

    out = copy.deepcopy(analysis)
    out_log = copy.deepcopy(log)
    situation = _situation(out)

    for entry in out_log:
        if not isinstance(entry, dict) or entry.get("status") != "verified":
            continue
        context = entry.get("context")
        statute_text = entry.get("statute_text")
        if not context or not statute_text:
            entry["adjudication"] = "unavailable"
            continue

        verdict, explanation = _call_haiku(key, entry, situation)
        if verdict is None:
            entry["adjudication"] = "unavailable"
            continue

        entry["adjudication"] = verdict
        entry["adjudication_explanation"] = explanation or ""
        if verdict in ("WRONG_SCOPE", "CONTRADICTS"):
            out, removed = scrub_exact_citation(
                out,
                entry.get("citation", ""),
                _SCOPE_NOTE.format(cite=entry.get("citation", "")),
            )
            entry["status"] = f"scrubbed_{verdict.lower()}"
            entry["removed"] = removed

    return out, out_log
