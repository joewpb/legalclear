"""Module 4 — Discovery Motion Analyzer Agent.

Analyzes Florida Motions for Discovery under FL Rule of Criminal
Procedure 3.220.  Supports PDF (text extraction) and image
(Claude vision) inputs.  Uses claude-sonnet-4-6 with structured
JSON output and SSE streaming.
"""

from __future__ import annotations

import base64
import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.agents.police_report_v2 import compute_risk_score
from src.core.citation_filter import StreamingCitationFilter
from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences
from src.core.url_filter import StreamingURLFilter, filter_json_strings
from src.ingestion.pdf_parser import PDFParser

logger = logging.getLogger(__name__)


def _ensure_dict(item, default_key="item"):
    """Convert dict-like objects to dicts with safe .get() fallbacks.

    If item is already a dict, return it.
    If item is a string, wrap it as {default_key: item}.
    Otherwise, return empty dict.
    """
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        return {default_key: item}
    logger.warning("Unexpected item type in LLM response: %r", item)
    return {}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You analyze Florida Motions for Discovery for pro se "
    "litigants. Under FL Rule of Criminal Procedure 3.220, "
    "a complete motion for discovery should address: "
    "witness lists, written statements, defendant statements, "
    "documents and tangible objects, reports of examinations "
    "and tests, expert witness information, and co-defendant "
    "statements where applicable. "
    "Analyze this motion and return: "
    "1. Plain English summary of what is being requested "
    "2. What is present and properly stated "
    "3. What is missing vs FL Rule 3.220 standard — "
    "   classify each by severity "
    "4. Discrepancies, vague language, or procedural "
    "   gaps — classify each by severity "
    "5. What the opposing party is likely to produce "
    "6. What the opposing party is likely to resist "
    "   producing — classify each by severity "
    "Third-person framing only. Never give legal advice. "
    "Return structured JSON: "
    "{ summary: string, what_requested: string[], "
    "what_present: string[], "
    "what_missing: [{ severity: 'high'|'medium'|'low', "
    "item: string, why_important: string, "
    "ask_attorney: string, page_ref: string | null }], "
    "discrepancies: [{ severity: 'high'|'medium'|'low', "
    "description: string, ask_attorney: string, "
    "page_ref: string | null }], "
    "likely_production: string[], "
    "likely_resistance: [{ severity: 'high'|'medium'|'low', "
    "item: string, reason: string, "
    "ask_attorney: string, page_ref: string | null }], "
    "disclaimer: string } "
    "Severity guide: high = critical omission or procedural "
    "violation of Rule 3.220; medium = notable gap or "
    "ambiguity; low = minor formatting or stylistic issue. "
    "ask_attorney: a plain-English question the user should "
    "raise with their defense attorney about this finding. "
    "page_ref: where in the motion this issue appears "
    "(e.g. 'p.2, paragraph 3'), or null if not page-specific."
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class DiscoveryMotionAnalyzer:
    """Streaming discovery-motion analyzer with vision support."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
        self._pdf_parser = PDFParser()

    # ── content builders ────────────────────────────────────────────────

    @staticmethod
    def _guess_media_type(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif",
            "webp": "image/webp",
        }.get(ext, "image/jpeg")

    @staticmethod
    def _is_image(filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}

    @staticmethod
    def _is_pdf(filename: str) -> bool:
        return filename.rsplit(".", 1)[-1].lower() == "pdf" if "." in filename else False

    def _build_text_message(self, text: str, lang_label: str) -> str:
        return (
            f"Analyze this Florida Motion for Discovery. "
            f"Respond entirely in {lang_label}. "
            "Return ONLY a valid JSON object. "
            "No markdown. No preamble.\n\n"
            f"Motion text:\n{text[:24000]}"
        )

    # ── streaming ───────────────────────────────────────────────────────

    async def analyze_stream(
        self, file_bytes: bytes, filename: str, language: str = "en",
    ) -> AsyncGenerator[str, None]:
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []

        if self._is_image(filename):
            media_type = self._guess_media_type(filename)
            b64 = base64.b64encode(file_bytes).decode("ascii")
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            })
            user_content.append({
                "type": "text",
                "text": (
                    f"Analyze this Florida Motion for Discovery. "
                    f"Respond entirely in {lang_label}. "
                    "Return ONLY a valid JSON object. No markdown. No preamble."
                ),
            })

        elif self._is_pdf(filename):
            try:
                extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
            except Exception:
                logger.error("PDF extraction failed:\n%s", traceback.format_exc())
                yield f"data: {json.dumps({'error': True, 'message': 'Could not extract text from this PDF.', 'disclaimer': get_disclaimer(language)})}\n\n"
                return
            raw_text = extraction.get("raw_text", "")
            if not raw_text.strip():
                yield f"data: {json.dumps({'error': True, 'message': 'No readable text found.', 'disclaimer': get_disclaimer(language)})}\n\n"
                return
            user_content.append({
                "type": "text",
                "text": self._build_text_message(raw_text, lang_label),
            })
        else:
            yield f"data: {json.dumps({'error': True, 'message': 'Unsupported file type.', 'disclaimer': get_disclaimer(language)})}\n\n"
            return

        emitted_content = False
        try:
            full_text = ""
            url_filter = StreamingURLFilter("discovery_motion")
            citation_filter = StreamingCitationFilter("discovery_motion")
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    emitted_content = True
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        yield f"data: {safe}\n\n"
            tail = citation_filter.feed(url_filter.flush())
            tail += citation_filter.flush()
            if tail:
                yield f"data: {tail}\n\n"

            yield (
                "event: disclaimer\n"
                f"data: {json.dumps({'disclaimer': get_disclaimer(language)})}\n\n"
            )

            # ── Post-stream: compute risk score deterministically ──
            try:
                parsed = json.loads(strip_markdown_fences(full_text))
                all_findings: list[dict] = []
                for d in parsed.get("discrepancies", []):
                    all_findings.append({
                        "severity": d.get("severity", "low"),
                        "description": d.get("description", ""),
                    })
                for m in parsed.get("what_missing", []):
                    obj = _ensure_dict(m, "item")
                    all_findings.append({
                        "severity": obj.get("severity", "low"),
                        "description": f"Missing: {obj.get('item', 'unknown')} — {obj.get('why_important', '')}",
                    })
                for r in parsed.get("likely_resistance", []):
                    obj = _ensure_dict(r, "item")
                    all_findings.append({
                        "severity": obj.get("severity", "low"),
                        "description": f"Likely resisted: {obj.get('item', 'unknown')} — {obj.get('reason', '')}",
                    })
                risk = compute_risk_score(all_findings)
                risk["type"] = "risk_analysis"
                yield f"data: {json.dumps(risk)}\n\n"
            except (json.JSONDecodeError, KeyError):
                logger.error(
                    "DiscoveryMotionAnalyzer risk-score parse failed:\n%s",
                    traceback.format_exc(),
                )

        except Exception:
            logger.error("DiscoveryMotionAnalyzer stream error:\n%s", traceback.format_exc())
            if emitted_content:
                yield (
                    "event: disclaimer\n"
                    f"data: {json.dumps({'disclaimer': get_disclaimer(language)})}\n\n"
                )
            yield f"data: {json.dumps({'error': True, 'message': 'Analysis could not be completed.', 'disclaimer': get_disclaimer(language)})}\n\n"

    # ── non-streaming ───────────────────────────────────────────────────

    async def analyze(self, file_bytes: bytes, filename: str, language: str = "en") -> dict:
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []

        if self._is_image(filename):
            b64 = base64.b64encode(file_bytes).decode("ascii")
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": self._guess_media_type(filename), "data": b64},
            })
        elif self._is_pdf(filename):
            try:
                extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
            except Exception:
                logger.error("PDF extraction failed in analyze:\n%s", traceback.format_exc())
                return {"error": True, "message": "Could not extract text.", "disclaimer": get_disclaimer(language)}
            raw_text = extraction.get("raw_text", "")
            if not raw_text.strip():
                return {"error": True, "message": "No readable text found.", "disclaimer": get_disclaimer(language)}
        else:
            return {"error": True, "message": "Unsupported file type.", "disclaimer": get_disclaimer(language)}

        user_content.append({
            "type": "text",
            "text": (
                f"Analyze this Florida Motion for Discovery. "
                f"Respond entirely in {lang_label}. "
                "Return ONLY a valid JSON object. No markdown. No preamble."
                + (f"\n\nMotion text:\n{raw_text[:24000]}" if self._is_pdf(filename) else "")
            ),
        })

        try:
            response = await self.client.messages.create(
                model=self.model, max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            )
            parsed = json.loads(strip_markdown_fences(response.content[0].text))
            parsed = filter_json_strings(parsed, "discovery_motion")
            parsed["disclaimer"] = get_disclaimer(language)

            # Compute deterministic risk score from findings
            all_findings: list[dict] = []
            for d in parsed.get("discrepancies", []):
                all_findings.append({
                    "severity": d.get("severity", "low"),
                    "description": d.get("description", ""),
                })
            for m in parsed.get("what_missing", []):
                obj = _ensure_dict(m, "item")
                all_findings.append({
                    "severity": obj.get("severity", "low"),
                    "description": f"Missing: {obj.get('item', 'unknown')} — {obj.get('why_important', '')}",
                })
            for r in parsed.get("likely_resistance", []):
                obj = _ensure_dict(r, "item")
                all_findings.append({
                    "severity": obj.get("severity", "low"),
                    "description": f"Likely resisted: {obj.get('item', 'unknown')} — {obj.get('reason', '')}",
                })
            parsed["risk_analysis"] = compute_risk_score(all_findings)
            return parsed
        except Exception:
            logger.error("DiscoveryMotionAnalyzer error:\n%s", traceback.format_exc())
            return {"error": True, "message": "Analysis could not be completed.", "disclaimer": get_disclaimer(language)}
