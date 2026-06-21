"""Module 5 — Property & Casualty Explainer Agent.

Explains Florida property and casualty legal situations.
Handles insurance_bad_faith (FL Statute 624.155) and
premises_liability.  Accepts entities from intake router
and optional document uploads (PDF/image).  Uses
claude-sonnet-4-6 with SSE streaming.
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
    "You explain Florida property and casualty legal "
    "situations to people with no legal background. "
    "For insurance_bad_faith: "
    "Cover what insurance bad faith means under FL Statute "
    "624.155, what the Civil Remedy Notice process is, "
    "what the 60-day cure period means, what typically "
    "happens in FL bad faith cases, what documentation "
    "is typically relevant (denial letters, policy, "
    "correspondence, estimates). "
    "For premises_liability: "
    "Cover what premises liability means in Florida, "
    "the duty of care owed by property owners, what "
    "comparative negligence means in FL, typical timeline "
    "for these cases, what documentation is typically "
    "relevant (incident reports, medical records, "
    "photos, witness info). "
    "For unknown sub_type: explain both and ask "
    "clarifying questions to identify which applies. "
    "Third-person framing only. Never give legal advice. "
    "Never state what someone should do. "
    "Return structured JSON: "
    "{ sub_type_identified: string, "
    "what_this_is: string, "
    "what_usually_happens: string, "
    "typical_timeline: string, "
    "relevant_florida_law: string, "
    "useful_documentation: string[], "
    "watch_out_for: string[], "
    "typical_outcomes: string[], "
    "clarifying_questions: string[] | null, "
    "disclaimer: string }"
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class PropertyCasualtyExplainer:
    """Streaming property & casualty explainer with optional document support."""

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
            "png": "image/png", "gif": "image/gif", "webp": "image/webp",
        }.get(ext, "image/jpeg")

    @staticmethod
    def _is_image(filename: str) -> bool:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif"}

    @staticmethod
    def _is_pdf(filename: str) -> bool:
        return filename.rsplit(".", 1)[-1].lower() == "pdf" if "." in filename else False

    @staticmethod
    def _strip_fences(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return text

    def _build_entities_text(self, entities: dict) -> str:
        """Format entities dict as readable context lines."""
        if not entities:
            return "No specific situation details provided."
        lines = ["Situation details:"]
        for k, v in entities.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def _build_user_text(
        self,
        sub_type: str,
        entities: dict,
        lang_label: str,
        doc_text: Optional[str] = None,
    ) -> str:
        """Assemble the main user prompt text."""
        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")
        parts.append(f"Sub-type: {sub_type}.")
        parts.append(self._build_entities_text(entities))

        if doc_text:
            parts.append(
                f"\nSupporting document text (up to 24,000 chars):\n"
                f"{doc_text[:24000]}"
            )

        parts.append(
            "Explain this Florida property/casualty situation. "
            "Return ONLY a valid JSON object. No markdown. No preamble."
        )
        return "\n".join(parts)

    # ── streaming ───────────────────────────────────────────────────────

    async def explain_stream(
        self,
        sub_type: str,
        entities: dict,
        language: str = "en",
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a property/casualty explanation as SSE chunks."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: Optional[str] = None

        # ── optional file ────────────────────────────────────────────
        if file_bytes and filename:
            if self._is_image(filename):
                media_type = self._guess_media_type(filename)
                b64 = base64.b64encode(file_bytes).decode("ascii")
                user_content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                })
            elif self._is_pdf(filename):
                try:
                    extraction = await self._pdf_parser.extract_from_bytes_async(file_bytes)
                except Exception:
                    logger.error("PDF extraction failed:\n%s", traceback.format_exc())
                    yield f"data: {json.dumps({'error': True, 'message': 'Could not extract text from PDF.', 'disclaimer': get_disclaimer(language)})}\n\n"
                    return
                doc_text = extraction.get("raw_text", "")
                if not doc_text.strip():
                    yield f"data: {json.dumps({'error': True, 'message': 'No readable text found.', 'disclaimer': get_disclaimer(language)})}\n\n"
                    return
            else:
                yield f"data: {json.dumps({'error': True, 'message': 'Unsupported file type.', 'disclaimer': get_disclaimer(language)})}\n\n"
                return

        # ── text portion ──────────────────────────────────────────────
        user_content.append({
            "type": "text",
            "text": self._build_user_text(sub_type, entities, lang_label, doc_text),
        })

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            ) as stream:
                async for chunk in stream.text_stream:
                    yield f"data: {chunk}\n\n"
        except Exception:
            logger.error("PropertyCasualtyExplainer stream error:\n%s", traceback.format_exc())
            yield f"data: {json.dumps({'error': True, 'message': 'Explanation could not be generated.', 'disclaimer': get_disclaimer(language)})}\n\n"

    # ── non-streaming ───────────────────────────────────────────────────

    async def explain(
        self,
        sub_type: str,
        entities: dict,
        language: str = "en",
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> dict:
        """Non-streaming explanation."""
        lang_label = "Spanish" if language == "es" else "English"
        user_content: list[dict] = []
        doc_text: Optional[str] = None

        if file_bytes and filename:
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
                    return {"error": True, "message": "Could not extract text.", "disclaimer": get_disclaimer(language)}
                doc_text = extraction.get("raw_text", "")

        user_content.append({
            "type": "text",
            "text": self._build_user_text(sub_type, entities, lang_label, doc_text),
        })

        try:
            response = await self.client.messages.create(
                model=self.model, max_tokens=4096,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_content}],
            )
            parsed = json.loads(self._strip_fences(response.content[0].text))
            parsed["disclaimer"] = get_disclaimer(language)
            return parsed
        except Exception:
            logger.error("PropertyCasualtyExplainer error:\n%s", traceback.format_exc())
            return {"error": True, "message": "Explanation could not be generated.", "disclaimer": get_disclaimer(language)}
