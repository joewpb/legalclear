import json
import logging
import traceback

from anthropic import AsyncAnthropic

from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS
from src.agents.small_claims_citations import SMALL_CLAIMS_CURATED_CITATIONS
from src.core.citation_resolver import resolve_citation
from src.core.config import settings
from src.core.citation_filter import StreamingCitationFilter, filter_citations_text
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences
from src.core.url_filter import StreamingURLFilter, filter_json_strings, strip_urls_final

logger = logging.getLogger(__name__)

# The generic explainer handles every uploaded document type, so it may cite
# only from the union of every module's curated set — not any single
# module's set alone. This union grows as more modules get curated sets
# (Dispatch J1/J2/J3 pattern: core.citation_resolver guard + a per-module
# curated dict). Coverage gaps degrade to silence, not fabrication — a real
# but uncurated citation is stripped exactly like a fabricated one.
EXPLAINER_CURATED_CITATIONS: dict = {
    **SMALL_CLAIMS_CURATED_CITATIONS,
    **EVICTION_CURATED_CITATIONS,
}
EXPLAINER_CITATION_LIST = [
    resolution.citation for resolution in EXPLAINER_CURATED_CITATIONS.values()
]


def _filter_citation_json_strings(obj, agent_name: str):
    """Recursively apply ``filter_citations_text`` to every string in a
    parsed JSON value — catches citations embedded in prose fields
    (summary, what_this_means_for_you, etc.), which the structured
    ``citations`` field guard (``filter_citations``) does not cover.
    """
    if isinstance(obj, dict):
        return {k: _filter_citation_json_strings(v, agent_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_filter_citation_json_strings(v, agent_name) for v in obj]
    if isinstance(obj, str):
        return filter_citations_text(obj, agent_name)
    return obj


def _generic_error_message(language: str) -> str:
    # Exception details go to the logger only — never into a user-facing
    # payload (CodeQL: information exposure through an exception).
    return ("No se pudo procesar la solicitud. Intente de nuevo."
            if language == "es"
            else "The request could not be processed. Please try again.")


_CITATION_LIST_TEXT = "; ".join(EXPLAINER_CITATION_LIST)

SYSTEM_PROMPT = (
    "You are a plain language legal document explainer "
    "for LegalClear. Your job is to help ordinary people "
    "with no legal background understand legal documents "
    "clearly and accurately. You use simple everyday language. "
    "You never use legal jargon without immediately explaining "
    "it in parentheses. You are thorough, warm, and clear. "
    "You give educated answers about what the document means, "
    "what the law says, and what options are available. "
    "You DO tell people what they should do — you're acting as "
    "a legal expert. End EVERY response by directing the user "
    "to confirm with a licensed Florida attorney before acting. "
    "Example ending: 'Confirm this with a Florida attorney before "
    "filing or responding. Free help: LegalClear /find-legal-help.' "
    "When the user's language is Spanish, respond entirely in "
    "Spanish including all JSON field values. Return valid JSON only. "
    "You may cite ONLY the following Florida Statutes citations, copied "
    "verbatim, and never invent, alter, or cite any other citation: "
    f"{_CITATION_LIST_TEXT}. If none of these citations is relevant to a "
    "section, omit a citation for that section rather than guessing. "
    "Include a citations field in the JSON: "
    "citations: [{ section: string, citation: string }]."
)


class ExplainerAgent:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    @staticmethod
    def filter_citations(raw_citations) -> list[dict]:
        """Strip any citation not resolvable against the union curated set.

        Never fails the response — an unresolvable citation is dropped, the
        section keeps its text. Applied to the explainer's structured
        ``citations`` field only, never to prose (prose-level citation
        filtering is a separate, unbuilt piece of work).
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
            match = resolve_citation(cite, EXPLAINER_CURATED_CITATIONS)
            if match is None:
                continue
            filtered.append({"section": item.get("section"), "citation": match.citation})
        return filtered

    async def explain(self, text: str, language: str = "en") -> dict:
        """Non-streaming explanation — kept for backward compatibility."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}]
            )
            content = response.content[0].text
            parsed = json.loads(strip_markdown_fences(content))
            parsed = filter_json_strings(parsed, "explainer")
            parsed = _filter_citation_json_strings(parsed, "explainer")
            parsed["citations"] = self.filter_citations(parsed.get("citations"))
            parsed["disclaimer"] = get_disclaimer(language)
            return parsed
        except Exception as e:
            logger.error(f"Explainer error: {e}\n{traceback.format_exc()}")
            return {
                "error": True,
                "message": _generic_error_message(language),
                "disclaimer": get_disclaimer(language)
            }

    async def explain_stream(self, text: str, language: str = "en"):
        """Streaming explanation — yields SSE chunks."""
        try:
            url_filter = StreamingURLFilter("explainer")
            citation_filter = StreamingCitationFilter("explainer")
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}]
            ) as stream:
                async for chunk in stream.text_stream:
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        yield f"data: {safe}\n\n"
            tail = citation_filter.feed(url_filter.flush())
            tail += citation_filter.flush()
            if tail:
                yield f"data: {tail}\n\n"
        except Exception as e:
            logger.error(f"Explainer stream error: {e}\n{traceback.format_exc()}")
            error_json = json.dumps({
                "error": True,
                "message": _generic_error_message(language),
                "disclaimer": get_disclaimer(language)
            })
            yield f"data: {error_json}\n\n"

    async def answer_question(self, document_id: str, question: str,
                            language: str = "en") -> dict:
        """Answer a specific question about a document."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": question}]
            )
            content = response.content[0].text
            return {
                "document_id": document_id,
                "question": question,
                "answer": strip_urls_final(content, "explainer"),
                "disclaimer": get_disclaimer(language)
            }
        except Exception as e:
            logger.error(f"Question error: {e}\n{traceback.format_exc()}")
            return {
                "error": True,
                "message": _generic_error_message(language),
                "disclaimer": get_disclaimer(language)
            }
