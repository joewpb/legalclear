"""Module 1 — Small Claims Explainer Agent.

Explains Florida small claims court in plain English for pro se litigants.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
"""

import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.agents.small_claims_citations import (
    SMALL_CLAIMS_CITATION_LIST,
    SMALL_CLAIMS_CURATED_CITATIONS,
)
from src.core.citation_filter import StreamingCitationFilter, filter_citations_text
from src.core.citation_resolver import resolve_citation
from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences
from src.core.url_filter import StreamingURLFilter, filter_json_strings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_CITATION_LIST_TEXT = "; ".join(SMALL_CLAIMS_CITATION_LIST)

SYSTEM_PROMPT = (
    "You explain Florida small claims court to people with no "
    "legal background. Florida small claims handles disputes up "
    "to $8,000 in county court. Use conditional, consequence-based "
    "framing rather than directives — describe what follows if the "
    "person files, and what follows if they do not, and develop both "
    "branches honestly and in comparable depth. "
    "If the person files: what jurisdiction and filing fees apply, "
    "what the filing process looks like, what happens at the hearing, "
    "the typical timeline (30-70 days to hearing in FL), what "
    "documentation is typically useful, and how a judgment is "
    "enforced if they win. "
    "If the person does not file: the claim stays unresolved, the "
    "other party is under no obligation to pay or act, and the "
    "statute of limitations keeps running toward the point the claim "
    "can no longer be brought at all. Where the amount in dispute is "
    "small relative to the time, cost, and effort of pursuing a claim, "
    "say plainly that not filing can be the reasonable choice — this "
    "is a real branch to develop with the same care as the filing "
    "branch, never a token line. "
    "Never issue directive advice telling the person what to do. "
    "State conditions and their consequences instead — 'If the "
    "person files within the limitations period, X. If the person "
    "does not, Y.' Never state deadlines as obligations. "
    "You may cite ONLY the following Florida Statutes citations, copied "
    "verbatim, and never invent, alter, or cite any other citation: "
    f"{_CITATION_LIST_TEXT}. If none of these citations is relevant to a "
    "section, omit a citation for that section rather than guessing. "
    "Return structured JSON: "
    "{ what_this_is: string, what_usually_happens: string, "
    "typical_timeline: string, useful_documentation: string[], "
    "watch_out_for: string[], typical_outcomes: string[], "
    "citations: [{ section: string, citation: string }], "
    "disclaimer: string }"
)

def _filter_citation_json_strings(obj, agent_name: str):
    """Recursively apply ``filter_citations_text`` to every string in a
    parsed JSON value — catches citations embedded in prose fields, which
    the structured ``citations`` field guard (``filter_citations``) does
    not cover.
    """
    if isinstance(obj, dict):
        return {k: _filter_citation_json_strings(v, agent_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_filter_citation_json_strings(v, agent_name) for v in obj]
    if isinstance(obj, str):
        return filter_citations_text(obj, agent_name)
    return obj


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
    def filter_citations(raw_citations) -> list[dict]:
        """Strip any citation not resolvable against the curated ch. 34 set.

        Never fails the response — an unresolvable citation is dropped, the
        section keeps its text. Applied to agent output, never to a prompt.
        """
        filtered: list[dict] = []
        if not isinstance(raw_citations, list):
            return filtered
        for item in raw_citations:
            if not isinstance(item, dict):
                continue
            cite = item.get("citation")
            if not cite:
                continue
            match = resolve_citation(cite, SMALL_CLAIMS_CURATED_CITATIONS)
            if match is None:
                continue
            filtered.append({"section": item.get("section"), "citation": match.citation})
        return filtered

    # ── streaming ───────────────────────────────────────────────────────

    async def explain_stream(
        self, entities: dict, language: str = "en"
    ) -> AsyncGenerator[str, None]:
        """Stream a small-claims explanation as SSE chunks."""
        user_prompt = self._build_user_prompt(entities, language)
        disclaimer = get_disclaimer(language)

        emitted_content = False
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
                url_filter = StreamingURLFilter("small_claims")
                citation_filter = StreamingCitationFilter("small_claims")
                full_text = ""
                async for chunk in stream.text_stream:
                    emitted_content = True
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        full_text += safe
                        yield f"data: {safe}\n\n"
                tail = citation_filter.feed(url_filter.flush())
                tail += citation_filter.flush()
                if tail:
                    full_text += tail
                    yield f"data: {tail}\n\n"

            try:
                parsed = json.loads(strip_markdown_fences(full_text))
                filtered_citations = self.filter_citations(parsed.get("citations"))
            except Exception:
                filtered_citations = []

            yield (
                "event: citations\n"
                f"data: {json.dumps({'citations': filtered_citations})}\n\n"
            )

            yield (
                "event: disclaimer\n"
                f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
            )

        except Exception:
            logger.error(
                "SmallClaimsExplainer stream error:\n%s",
                traceback.format_exc(),
            )
            if emitted_content:
                yield (
                    "event: disclaimer\n"
                    f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
                )
            error_payload = json.dumps(
                {
                    "error": True,
                    "message": "Explanation could not be generated.",
                    "disclaimer": disclaimer,
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
            parsed = json.loads(strip_markdown_fences(raw))
            parsed = _filter_citation_json_strings(parsed, "small_claims")
            parsed["citations"] = self.filter_citations(parsed.get("citations"))
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
