import json
import logging
import traceback

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences
from src.core.url_filter import StreamingURLFilter, filter_json_strings, strip_urls_final

logger = logging.getLogger(__name__)


def _generic_error_message(language: str) -> str:
    # Exception details go to the logger only — never into a user-facing
    # payload (CodeQL: information exposure through an exception).
    return ("No se pudo procesar la solicitud. Intente de nuevo."
            if language == "es"
            else "The request could not be processed. Please try again.")


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
    "Spanish including all JSON field values. Return valid JSON only."
)


class ExplainerAgent:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

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
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}]
            ) as stream:
                async for chunk in stream.text_stream:
                    safe = url_filter.feed(chunk)
                    if safe:
                        yield f"data: {safe}\n\n"
            tail = url_filter.flush()
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
