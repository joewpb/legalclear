import json
import logging
import traceback

from anthropic import AsyncAnthropic

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.json_utils import strip_markdown_fences

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a legal document risk scanner for LegalClear. "
    "You identify clauses and terms that are unusual, "
    "potentially harmful, one-sided, or worth careful "
    "attention. You score risk clearly using RED, YELLOW, "
    "or GREEN. You explain why each item matters in plain "
    "language a non-lawyer can understand. You are thorough, "
    "direct, and never alarmist. When the user's language is "
    "Spanish, respond entirely in Spanish. Return valid JSON "
    "only. No preamble. No markdown. JSON only.\n\n"
    "RED = significantly harmful, one-sided, or dangerous\n"
    "YELLOW = unusual, worth negotiating, needs attention\n"
    "GREEN = standard, fair, and reasonable"
)


class RiskScannerAgent:

    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
            timeout=120.0,
        )
        self.model = "claude-haiku-4-5-20251001"

    async def scan(self, document: dict,
                   classification: dict,
                   lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )

        user_prompt = f"""Language: {lang}
{spanish}
Document type: {classification.get("document_type")}
Category: {classification.get("document_category")}
Jurisdiction: {classification.get("jurisdiction_name")}

Scan this document for risk. Return JSON with:

overall_risk_level: one of: LOW, MEDIUM, HIGH

risk_summary: 2-3 sentence plain language assessment

clauses: list of objects each with:
  clause_title, risk_level (RED/YELLOW/GREEN),
  what_it_says, why_it_matters, what_to_do,
  quote (max 100 chars verbatim)

missing_protections: list of objects each with:
  protection_name, why_important, what_to_ask_for

red_count: integer
yellow_count: integer
green_count: integer

top_concerns: list of exactly 3 strings in order
of severity

negotiation_tips: list of tips if signable contract,
empty list otherwise

Document text:
{document.get("text", "")[:60000]}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }]
            )
            raw = response.content[0].text
            result = json.loads(strip_markdown_fences(raw))
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            return result
        except Exception as e:
            logger.error(
                "Anthropic call failed in %s: %s\n%s",
                self.__class__.__name__,
                repr(e),
                traceback.format_exc()
            )
            return {"error": True,
                    "message": ("No se pudo procesar la solicitud. Intente de nuevo."
                                if lang == "es"
                                else "The request could not be processed. Please try again."),
                    "disclaimer": get_disclaimer(
                        lang, "standard")}
