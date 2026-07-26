"""Module 1 — Small Claims Explainer Agent.

Explains Florida small claims court in plain English for pro se litigants.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
"""

import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You explain Florida small claims court to people with no "
    "legal background. Florida small claims handles disputes up "
    "to $8,000 in county court. Cover: what small claims court "
    "is, what the filing process looks like, what happens at the "
    "hearing, typical timeline (30-70 days to hearing in FL), "
    "what documentation is typically useful, what outcomes "
    "typically occur for this dispute type. "
    "Third-person framing only. Never say 'you should' or "
    "'you must'. Never state deadlines as obligations. "
    "Return structured JSON: "
    "{ what_this_is: string, what_usually_happens: string, "
    "typical_timeline: string, useful_documentation: string[], "
    "watch_out_for: string[], typical_outcomes: string[], "
    "disclaimer: string }"
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class SmallClaimsExplainer:
    """Streaming explainer for Florida small claims court."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    # ── prompt builder ──────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(entities: dict, language: str) -> str:
        """Build a user prompt from the intake router's entities."""
        lang_label = "Spanish" if language == "es" else "English"

        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")

        if entities:
            parts.append("Context from the user's situation:")
            for key, value in entities.items():
                parts.append(f"  {key}: {value}")

        parts.append(
            "Explain Florida small claims court as it relates to this "
            "situation. Cover what small claims court is, what the "
            "filing process looks like, what happens at the hearing, "
            "the typical timeline, useful documentation, things to "
            "watch out for, and typical outcomes for this dispute type."
        )
        parts.append(
            "Return ONLY a valid JSON object. No markdown. No preamble."
        )

        return "\n".join(parts)

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _strip_fences(raw: str) -> str:
        """Remove optional ``` fences from an LLM response."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            text = text.removeprefix("json")
            text = text.strip()
        return text

    # ── streaming ───────────────────────────────────────────────────────

    async def explain_stream(
        self, entities: dict, language: str = "en"
    ) -> AsyncGenerator[str, None]:
        """Stream a small-claims explanation as SSE chunks."""
        user_prompt = self._build_user_prompt(entities, language)

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
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for chunk in stream.text_stream:
                    yield f"data: {chunk}\n\n"

        except Exception:
            logger.error(
                "SmallClaimsExplainer stream error:\n%s",
                traceback.format_exc(),
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

    async def explain(self, entities: dict, language: str = "en") -> dict:
        """Non-streaming explanation.  Useful for testing and debugging."""
        user_prompt = self._build_user_prompt(entities, language)

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
            parsed = json.loads(self._strip_fences(raw))
            parsed["disclaimer"] = get_disclaimer(language)
            return parsed

        except Exception:
            logger.error(
                "SmallClaimsExplainer error:\n%s",
                traceback.format_exc(),
            )
            return {
                "error": True,
                "message": "Explanation could not be generated.",
                "disclaimer": get_disclaimer(language),
            }
