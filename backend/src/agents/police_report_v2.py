"""Module 3 — Police Report Analyzer V2 Agent.

Analyzes Florida police reports for pro se litigants.
Supports PDF (text extraction) and image (Claude vision) inputs.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import (
    TIGHTENED_PROMPT_SUFFIX,
    parse_llm_json_ladder,
)
from src.core.json_utils import (
    ladder_call_async as _ladder_call,
)
from src.core.url_filter import filter_json_strings
from src.ingestion.pdf_parser import PDFParser
from src.services.citation_adjudication import adjudicate_verified_citations
from src.services.citation_validation import validate_analysis_citations
from src.services.opinion_retrieval import (
    derive_situation_tags,
    generate_attorney_questions,
    get_relevant_opinions,
)

logger = logging.getLogger(__name__)


def _sse(event: str, payload: dict) -> str:
    """Frame one complete typed SSE event (event: line + one data: line).

    Phase A protocol: every frame carries an explicit event name and a
    single complete JSON data payload. No per-token fragments.
    """
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You analyze Florida police reports for pro se litigants. "
    "Extract and explain in plain English: "
    "1. What the report documents (incident type, date, location) "
    "2. Who is listed (officers, parties, witnesses) "
    "3. What charges or violations are cited and what they mean "
    "4. Miranda rights — were they noted as read "
    "5. Probable cause statement — is one present and what "
    "   does it say "
    "6. Discrepancies, inconsistencies, or missing standard "
    "   fields in the report — classify each by severity "
    "7. What typically happens next after this type of report "
    "Third-person framing only. Never give legal advice. "
    "Return structured JSON: "
    "{ incident_summary: string, parties: string[], "
    "charges_explained: [{ charge: string, "
    "plain_english: string }], "
    "miranda_noted: boolean | null, "
    "probable_cause_present: boolean | null, "
    "probable_cause_summary: string | null, "
    "discrepancies: [{ severity: 'high'|'medium'|'low', "
    "defect_category: "
    "'miranda'|'fourth_amendment'|'due_process'|"
    "'language_access'|'chain_of_custody'|'procedural'|null, "
    "description: string, ask_attorney: string, "
    "page_ref: string | null }], "
    "missing_fields: [{ severity: 'high'|'medium'|'low', "
    "field_name: string, why_important: string, "
    "page_ref: string | null }], "
    "what_happens_next: string, disclaimer: string } "
    "Severity guide: high = critical procedural error or "
    "constitutional violation; medium = notable inconsistency "
    "or missing standard field; low = minor formatting or "
    "typographical issue. "
    "ask_attorney: a plain-English question the user should "
    "raise with their defense attorney about this finding. "
    "defect_category: classify the constitutional or procedural "
    "nature of each discrepancy using exactly one value, or null "
    "if none fit. 'miranda' = missing/late Miranda warning in a "
    "custodial setting; 'fourth_amendment' = search/seizure, "
    "consent, probable-cause, or stop-and-frisk issue; "
    "'due_process' = fairness/notice/evidentiary due-process "
    "problem; 'language_access' = interpreter/translation access "
    "denied or absent for a limited-English person; "
    "'chain_of_custody' = evidence handling/continuity gap; "
    "'procedural' = other required-step omission. Always set "
    "defect_category from the issue itself, not from the "
    "miranda_noted / probable_cause_present booleans. "
    "page_ref: where in the report this issue appears "
    "(e.g. 'p.2, paragraph 3'), or null if not page-specific."
)

# ---------------------------------------------------------------------------
# Supported image MIME types for Claude vision
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

# ---------------------------------------------------------------------------
# Deterministic risk scoring — LLM classifies severity; Python computes score
# ---------------------------------------------------------------------------


def compute_risk_score(findings: list[dict]) -> dict:
    """Compute a numeric risk score from LLM-classified findings.

    LLM assigns severity (high/medium/low) per finding. This function
    computes the weighted score deterministically — the LLM never
    produces a number.
    """
    high = sum(1 for f in findings if f.get("severity") == "high")
    medium = sum(1 for f in findings if f.get("severity") == "medium")
    low = sum(1 for f in findings if f.get("severity") == "low")

    # Weighted score: high=3, medium=2, low=1
    score = high * 3 + medium * 2 + low * 1

    if score == 0:
        level = "LOW"
        summary = (
            "No significant risk indicators were identified "
            "in this report."
        )
        concerns: list[str] = []
    elif score <= 3:
        level = "MEDIUM"
        summary = (
            "This report contains a few notable issues that "
            "warrant attention but are not critical on their own."
        )
        concerns = [
            f.get("description", "") for f in findings
            if f.get("severity") in ("high", "medium")
        ][:3]
    elif score <= 6:
        level = "HIGH"
        summary = (
            "Multiple significant issues were identified in "
            "this report. These should be reviewed carefully "
            "with a defense attorney."
        )
        concerns = [
            f.get("description", "") for f in findings
            if f.get("severity") in ("high", "medium")
        ][:3]
    else:
        level = "CRITICAL"
        summary = (
            "This report contains critical procedural and "
            "factual issues. Immediate attorney review is "
            "strongly recommended."
        )
        concerns = [
            f.get("description", "") for f in findings
            if f.get("severity") in ("high", "medium")
        ][:3]

    return {
        "risk_score": score,
        "risk_level": level,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "risk_summary": summary,
        "top_concerns": concerns,
    }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class PoliceReportAnalyzerV2:
    """Streaming police report analyzer with vision support."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self._pdf_parser = PDFParser()

    # ── content builders ────────────────────────────────────────────────

    @staticmethod
    def _guess_media_type(filename: str) -> str:
        """Guess MIME type from file extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mapping = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return mapping.get(ext, "image/jpeg")

    @staticmethod
    def _is_image(filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}

    @staticmethod
    def _is_pdf(filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext == "pdf"

    # ── helpers ─────────────────────────────────────────────────────────

    # ── streaming ───────────────────────────────────────────────────────

    async def analyze_stream(
        self,
        file_bytes: bytes,
        filename: str,
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        """Stream a police report analysis as SSE chunks.

        PDF files: text is extracted, then sent to Claude.
        Image files: file is base64-encoded and sent to Claude vision.
        """
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []

        if self._is_image(filename):
            # ── Vision path ──────────────────────────────────────────
            media_type = self._guess_media_type(filename)
            b64 = base64.b64encode(file_bytes).decode("ascii")

            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                }
            )
            user_content.append(
                {
                    "type": "text",
                    "text": (
                        f"Analyze this Florida police report. "
                        f"Respond entirely in {lang_label}. "
                        "Return ONLY a valid JSON object. "
                        "No markdown. No preamble."
                    ),
                }
            )

        elif self._is_pdf(filename):
            # ── PDF text-extraction path ─────────────────────────────
            try:
                extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
            except Exception:
                logger.error("PDF extraction failed:\n%s", traceback.format_exc())
                yield _sse("error", {
                    "type": "error",
                    "error": True,
                    "message": "Could not extract text from this PDF.",
                    "disclaimer": get_disclaimer(language),
                })
                return

            raw_text = extraction.get("raw_text", "")
            if not raw_text.strip():
                yield _sse("error", {
                    "type": "error",
                    "error": True,
                    "message": (
                        "No readable text found in this PDF. "
                        "Try uploading an image of the report instead."
                    ),
                    "disclaimer": get_disclaimer(language),
                })
                return

            user_content.append(
                {
                    "type": "text",
                    "text": (
                        f"Analyze this Florida police report. "
                        f"Respond entirely in {lang_label}. "
                        "Return ONLY a valid JSON object. "
                        "No markdown. No preamble.\n\n"
                        f"Report text:\n{raw_text[:24000]}"
                    ),
                }
            )

        else:
            yield _sse("error", {
                "type": "error",
                "error": True,
                "message": "Unsupported file type. Please upload a PDF or image file.",
                "disclaimer": get_disclaimer(language),
            })
            return

        # ── Call Claude ─────────────────────────────────────────────────
        try:
            # Phase A: buffer the full LLM text locally. Nothing is emitted
            # per token anymore — every frame below is a complete typed
            # payload (analysis_json as ONE frame, plus risk_analysis /
            # relevant_opinions / case_context / progress / error).
            yield _sse("progress", {"type": "progress", "stage": "analyzing"})
            full_text = ""
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk

            # ── Post-stream: compute risk score deterministically ──
            async def _retry_analysis() -> str:
                # Decision 20: one tightened re-call to recover the JSON.
                content = list(user_content)
                content.append({"type": "text", "text": TIGHTENED_PROMPT_SUFFIX.strip()})
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[{"role": "user", "content": content}],
                )
                return response.content[0].text

            parsed, degraded = await parse_llm_json_ladder(
                full_text,
                site="police_report_v2",
                expect="dict",
                retry_call=_retry_analysis,
            )
            if degraded:
                # Decision 20: the ladder gave up. Emit a typed error frame
                # instead of ending the stream silently with no analysis.
                yield _sse("error", {
                    "type": "error",
                    "error": True,
                    "message": "Analysis could not be completed. Please try again.",
                    "disclaimer": get_disclaimer(language),
                })
                return

            # Analysis JSON as ONE complete frame (no per-token fragments).
            parsed = filter_json_strings(parsed, "police_report_v2")
            parsed["disclaimer"] = get_disclaimer(language)

            # Phase C1: deterministic citation validation (zero LLM) runs
            # BEFORE the analysis reaches the user — court-only chapter
            # citations (Ch. 90 Evidence Code, rules of court, bar rules)
            # and citations the statutes corpus cannot verify are scrubbed
            # from the LLM's claims, with plain-English notes. Charge
            # citations (document facts) are never touched. Never breaks
            # the response: on failure the analysis passes through
            # untouched with an empty log.
            try:
                parsed, citations_checked = validate_analysis_citations(parsed)
                parsed["citations_checked"] = citations_checked
            except Exception:
                logger.error(
                    "citation validation failed; emitting unvalidated "
                    "analysis:\n%s",
                    traceback.format_exc(),
                )
                parsed["citations_checked"] = []

            # Phase C2: per-citation Haiku adjudication (SUPPORTED /
            # WRONG_SCOPE / CONTRADICTS) on the verified citations only.
            # The deterministic C1 floor always wins — the LLM selects
            # which canned action fires, deterministic code applies it.
            # Offloaded to a thread (blocking requests). Never breaks the
            # response.
            if parsed.get("citations_checked"):
                try:
                    parsed, adjudicated = await asyncio.to_thread(
                        adjudicate_verified_citations,
                        parsed,
                        parsed["citations_checked"],
                    )
                    parsed["citations_checked"] = adjudicated
                except Exception:
                    logger.error(
                        "citation adjudication failed; emitting validated "
                        "but unadjudicated analysis:\n%s",
                        traceback.format_exc(),
                    )

            yield f"event: analysis_json\ndata: {json.dumps(parsed)}\n\n"

            all_findings = (
                parsed.get("discrepancies", [])
                + [
                    {
                        "severity": mf.get("severity", "low"),
                        "description": (
                            f"Missing field: {mf.get('field_name', 'unknown')} — "
                            f"{mf.get('why_important', '')}"
                        ),
                    }
                    for mf in parsed.get("missing_fields", [])
                ]
            )
            risk = compute_risk_score(all_findings)
            risk["type"] = "risk_analysis"
            yield _sse("risk_analysis", risk)

            # ── Post-stream: retrieve relevant opinions (Stage 2) ──
            # Sealed in its own try/except: risk_analysis (and the full
            # analysis JSON) have already been sent above, so a failure
            # here must NEVER bubble to the outer `except Exception`,
            # which would emit a misleading error event after a
            # successful analysis. Log + skip instead. `parsed` is
            # guaranteed non-None here — a degraded parse returned early.
            yield _sse("progress", {
                "type": "progress",
                "stage": "retrieving_case_law",
            })
            try:
                tags = derive_situation_tags(parsed)
                # get_relevant_opinions() does synchronous Supabase I/O
                # (supabase-py is blocking); offload it so the network
                # round-trip doesn't stall the event loop and every
                # other in-flight SSE client on this worker.
                # `parsed` is passed as analysis_result so the
                # retrieval service can derive fact terms from the
                # LLM's discrepancy/missing-field/charge text and rank
                # opinions by relevance (2026-08 relevance fix).
                opinions = await asyncio.to_thread(
                    get_relevant_opinions, tags, 3, parsed
                )
                # Generate specific attorney questions per opinion
                opinions = await asyncio.to_thread(
                    generate_attorney_questions, parsed, opinions,
                )
                yield _sse("relevant_opinions", {
                    "type": "relevant_opinions",
                    "situation_tags_used": tags,
                    "opinions": opinions,
                })
            except Exception:
                logger.error(
                    "relevant_opinions emission failed:\n%s",
                    traceback.format_exc(),
                )

            # ── Post-stream: extract case_context (Phase 9) ──
            # Lazy import: scanner imports compute_risk_score from this
            # module, so a top-level import here creates a cycle that
            # breaks app import (src.api.routes). Defer to call site.
            from src.agents.scanner import extract_case_context

            try:
                ctx = await extract_case_context([{
                    "filename": filename,
                    "text": raw_text if raw_text else "",
                }])
                yield _sse("case_context", {
                    "type": "case_context",
                    "case_context": ctx,
                })
            except Exception:
                logger.error(
                    "case_context extraction failed:\n%s",
                    traceback.format_exc(),
                )

        except Exception:
            logger.error(
                "PoliceReportAnalyzerV2 stream error:\n%s",
                traceback.format_exc(),
            )
            yield _sse("error", {
                "type": "error",
                "error": True,
                "message": "Analysis could not be completed.",
                "disclaimer": get_disclaimer(language),
            })

    # ── non-streaming (testing / debug) ─────────────────────────────────

    async def analyze(
        self,
        file_bytes: bytes,
        filename: str,
        language: str = "en",
    ) -> dict:
        """Non-streaming analysis.  Useful for testing."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []

        if self._is_image(filename):
            media_type = self._guess_media_type(filename)
            b64 = base64.b64encode(file_bytes).decode("ascii")
            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                }
            )
        elif self._is_pdf(filename):
            try:
                extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
            except Exception:
                logger.error("PDF extraction failed in analyze:\n%s", traceback.format_exc())
                return {
                    "error": True,
                    "message": "Could not extract text from this PDF.",
                    "disclaimer": get_disclaimer(language),
                }
            raw_text = extraction.get("raw_text", "")
            if not raw_text.strip():
                return {
                    "error": True,
                    "message": "No readable text found in this PDF.",
                    "disclaimer": get_disclaimer(language),
                }
        else:
            return {
                "error": True,
                "message": "Unsupported file type.",
                "disclaimer": get_disclaimer(language),
            }

        user_content.append(
            {
                "type": "text",
                "text": (
                    f"Analyze this Florida police report. "
                    f"Respond entirely in {lang_label}. "
                    "Return ONLY a valid JSON object. "
                    "No markdown. No preamble."
                    + (
                        f"\n\nReport text:\n{raw_text[:24000]}"
                        if self._is_pdf(filename)
                        else ""
                    )
                ),
            }
        )

        async def _call(prompt: str) -> str:
            msg_content = user_content
            if prompt:  # retry pass: append the tightened instruction
                msg_content = list(user_content) + [{"type": "text", "text": prompt}]
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": msg_content}],
            )
            return response.content[0].text

        try:
            parsed, degraded = await _ladder_call(
                _call, "", site="police_report_v2_analyze", expect="dict"
            )
            if degraded:
                return {
                    "error": True,
                    "message": "Analysis could not be completed.",
                    "disclaimer": get_disclaimer(language),
                }
            parsed = filter_json_strings(parsed, "police_report_v2")
            parsed["disclaimer"] = get_disclaimer(language)

            # Compute deterministic risk score from findings
            all_findings = (
                parsed.get("discrepancies", [])
                + [
                    {
                        "severity": mf.get("severity", "low"),
                        "description": (
                            f"Missing field: {mf.get('field_name', 'unknown')} — "
                            f"{mf.get('why_important', '')}"
                        ),
                    }
                    for mf in parsed.get("missing_fields", [])
                ]
            )
            parsed["risk_analysis"] = compute_risk_score(all_findings)
            return parsed

        except Exception:
            logger.error(
                "PoliceReportAnalyzerV2 error:\n%s",
                traceback.format_exc(),
            )
            return {
                "error": True,
                "message": "Analysis could not be completed.",
                "disclaimer": get_disclaimer(language),
            }
