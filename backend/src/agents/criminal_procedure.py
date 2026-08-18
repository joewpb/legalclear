"""Module 2 — Criminal Procedure Explainer Agent.

Explains Florida criminal procedure in plain English for pro se litigants.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
"""

import asyncio
import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.citation_filter import StreamingCitationFilter
from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences
from src.core.url_filter import StreamingURLFilter, filter_json_strings
from src.services.opinion_retrieval import (
    derive_criminal_tags,
    generate_attorney_questions,
    get_relevant_opinions,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You explain Florida criminal procedure to people with no "
    "legal background. Explain the FL criminal process from "
    "the person's current stage forward through resolution. "
    "Cover: what each upcoming stage means in plain English, "
    "typical duration of each stage in Florida courts, "
    "what public defenders do and how they are assigned, "
    "what bond hearings typically involve in FL, "
    "what plea arrangements typically look like for this "
    "charge type and severity in Florida. "
    "Third-person framing only. Never give legal advice. "
    "Never state what someone should do. "
    "Return structured JSON: "
    "{ current_stage_explanation: string, "
    "next_stages: [{ stage: string, what_happens: string, "
    "typical_duration: string }], "
    "typical_timeline: string, "
    "key_people_involved: string[], "
    "what_usually_happens: string, "
    "typical_outcomes: string[], "
    "disclaimer: string }"
)

# ---------------------------------------------------------------------------
# Stage ordering
# ---------------------------------------------------------------------------

STAGE_ORDER = [
    "arrested",
    "charged",
    "arraigned",
    "pretrial",
    "trial",
    "sentencing",
]


def _stages_after(current: str) -> list[str]:
    """Return the list of stages that come after *current*."""
    try:
        idx = STAGE_ORDER.index(current.lower())
    except ValueError:
        idx = -1
    return STAGE_ORDER[idx + 1 :] if idx >= 0 else STAGE_ORDER


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class CriminalProcedureExplainer:
    """Streaming explainer for Florida criminal procedure."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    # ── prompt builder ──────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(
        charge_type: str,
        severity: str,
        current_stage: str,
        language: str,
    ) -> str:
        """Build a user prompt from the intake / entity data."""
        lang_label = "Spanish" if language == "es" else "English"
        upcoming = _stages_after(current_stage)

        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")
        parts.append(
            f"The person is currently at the '{current_stage}' stage "
            f"of the Florida criminal process."
        )
        parts.append(f"Charge type: {charge_type}.")
        parts.append(f"Severity: {severity}.")
        if upcoming:
            parts.append(
                f"Upcoming stages after '{current_stage}': "
                f"{', '.join(upcoming)}."
            )
        parts.append(
            "Explain the criminal process starting from this stage. "
            "Include a plain-English description of the current stage, "
            "what happens at each upcoming stage, typical durations, "
            "key people involved, bond hearings in FL, public defender "
            "assignment, and typical plea arrangements for this charge "
            "type and severity."
        )
        parts.append(
            "Return ONLY a valid JSON object. No markdown. No preamble."
        )

        return "\n".join(parts)

    # ── helpers ─────────────────────────────────────────────────────────

    # ── streaming ───────────────────────────────────────────────────────

    async def explain_stream(
        self,
        charge_type: str,
        severity: str,
        current_stage: str,
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        """Stream a criminal-procedure explanation as SSE chunks.

        After the LLM stream completes, derives situation_tags from the
        parsed result, fetches relevant FL court opinions, generates
        attorney questions, and emits a ``relevant_opinions`` SSE event.
        """
        user_prompt = self._build_user_prompt(
            charge_type, severity, current_stage, language
        )

        emitted_content = False
        try:
            full_text = ""
            url_filter = StreamingURLFilter("criminal_procedure")
            citation_filter = StreamingCitationFilter("criminal_procedure")
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
                messages=[{"role": "user", "content": user_prompt}],
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

            # ── Post-stream: retrieve relevant opinions ──
            parsed = None
            try:
                parsed = json.loads(strip_markdown_fences(full_text))
            except (json.JSONDecodeError, KeyError):
                logger.error(
                    "CriminalProcedureExplainer JSON parse failed"
                )
                # Opinion retrieval is best-effort — the explanation
                # JSON has already been streamed to the client, so a
                # parse failure here must not emit a misleading error
                # event.  Log + return without opinions.
                return

            if parsed:
                try:
                    tags = derive_criminal_tags(
                        parsed,
                        charge_type=charge_type,
                        severity=severity,
                        current_stage=current_stage,
                    )
                    opinions = await asyncio.to_thread(
                        get_relevant_opinions, tags
                    )
                    opinions = await asyncio.to_thread(
                        generate_attorney_questions, parsed, opinions,
                    )
                    opinions_payload = json.dumps({
                        "type": "relevant_opinions",
                        "situation_tags_used": tags,
                        "opinions": opinions,
                    })
                    yield f"data: {opinions_payload}\n\n"
                except Exception:
                    logger.error(
                        "CriminalProcedureExplainer opinion "
                        "retrieval failed:\n%s",
                        traceback.format_exc(),
                    )

        except Exception:
            logger.error(
                "CriminalProcedureExplainer stream error:\n%s",
                traceback.format_exc(),
            )
            if emitted_content:
                yield (
                    "event: disclaimer\n"
                    f"data: {json.dumps({'disclaimer': get_disclaimer(language)})}\n\n"
                )
            error_payload = json.dumps(
                {
                    "error": True,
                    "message": "Explanation could not be generated.",
                    "disclaimer": get_disclaimer(language),
                }
            )
            yield f"data: {error_payload}\n\n"

    # ── non-streaming (backward compat / testing) ───────────────────────

    async def explain(
        self,
        charge_type: str,
        severity: str,
        current_stage: str,
        language: str = "en",
    ) -> dict:
        """Non-streaming explanation.  Useful for testing and debugging."""
        user_prompt = self._build_user_prompt(
            charge_type, severity, current_stage, language
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
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
            parsed = json.loads(strip_markdown_fences(raw))
            parsed = filter_json_strings(parsed, "criminal_procedure")
            parsed["disclaimer"] = get_disclaimer(language)
            return parsed

        except Exception:
            logger.error(
                "CriminalProcedureExplainer error:\n%s",
                traceback.format_exc(),
            )
            return {
                "error": True,
                "message": "Explanation could not be generated.",
                "disclaimer": get_disclaimer(language),
            }
