"""Module 3 — Police Report Analyzer V2 Agent.

Analyzes Florida police reports for pro se litigants.
Supports PDF (text extraction) and image (Claude vision) inputs.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
"""

from __future__ import annotations

import base64
import json
import logging
import traceback
from typing import AsyncGenerator, Optional

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.ingestion.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

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
    "   fields in the report "
    "7. What typically happens next after this type of report "
    "Third-person framing only. Never give legal advice. "
    "Return structured JSON: "
    "{ incident_summary: string, parties: string[], "
    "charges_explained: [{ charge: string, "
    "plain_english: string }], "
    "miranda_noted: boolean | null, "
    "probable_cause_present: boolean | null, "
    "probable_cause_summary: string | null, "
    "discrepancies: string[], missing_fields: string[], "
    "what_happens_next: string, disclaimer: string }"
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

    @staticmethod
    def _strip_fences(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return text

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
                error_payload = json.dumps(
                    {
                        "error": True,
                        "message": "Could not extract text from this PDF.",
                        "disclaimer": get_disclaimer(language),
                    }
                )
                yield f"data: {error_payload}\n\n"
                return

            raw_text = extraction.get("raw_text", "")
            if not raw_text.strip():
                error_payload = json.dumps(
                    {
                        "error": True,
                        "message": "No readable text found in this PDF. Try uploading an image of the report instead.",
                        "disclaimer": get_disclaimer(language),
                    }
                )
                yield f"data: {error_payload}\n\n"
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
            error_payload = json.dumps(
                {
                    "error": True,
                    "message": "Unsupported file type. Please upload a PDF or image file.",
                    "disclaimer": get_disclaimer(language),
                }
            )
            yield f"data: {error_payload}\n\n"
            return

        # ── Call Claude ─────────────────────────────────────────────────
        try:
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
                    yield f"data: {chunk}\n\n"

        except Exception:
            logger.error(
                "PoliceReportAnalyzerV2 stream error:\n%s",
                traceback.format_exc(),
            )
            error_payload = json.dumps(
                {
                    "error": True,
                    "message": "Analysis could not be completed.",
                    "disclaimer": get_disclaimer(language),
                }
            )
            yield f"data: {error_payload}\n\n"

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

        try:
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
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text
            parsed = json.loads(self._strip_fences(raw))
            parsed["disclaimer"] = get_disclaimer(language)
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
