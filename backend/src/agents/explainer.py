import json
import logging
import traceback
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a plain language legal document explainer "
    "for LegalClear. Your job is to help ordinary people "
    "with no legal background understand legal documents "
    "clearly and accurately. You use simple everyday language. "
    "You never use legal jargon without immediately explaining "
    "it in parentheses. You are thorough, warm, and clear. "
    "You never give legal advice — you explain what documents "
    "say, not what people should do. When the user's language "
    "is Spanish, respond entirely in Spanish including all "
    "JSON field values. Return valid JSON only. "
    "No preamble. No markdown. JSON only."
)


class ExplainerAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
            timeout=120.0,
        )
        self.model = "claude-sonnet-4-6"

    async def explain(self, document: dict,
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
Parties: {", ".join(classification.get("parties", []))}
Complexity: {classification.get("estimated_complexity")}

Explain this document in plain language.
Return JSON with exactly these fields:

summary: 2-3 sentence plain language summary

what_this_means_for_you: 3-5 sentences on real-world
impact — what the reader agrees to, rights they have,
obligations they take on

key_sections: list of 5-8 most important sections, each
with: title, plain_explanation, importance
(one of: high, medium, low)

important_numbers: list of dollar amounts, percentages,
timeframes, deadlines, each with: label, value, context

your_rights: list of strings describing reader rights

your_obligations: list of strings describing obligations

questions_to_ask: list of 3-5 smart questions to ask
before signing or responding

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
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
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
            result["disclaimer"] = get_disclaimer(
                lang, "standard")
            result["language"] = lang
            return result
        except Exception as e:
            logger.error(
                "Anthropic call failed in %s: %s\n%s",
                self.__class__.__name__,
                repr(e),
                traceback.format_exc()
            )
            return {
                "error": True,
                "message": "An error occurred. Please try again.",
                "disclaimer": get_disclaimer(
                    lang, "standard"),
                "language": lang
            }

    async def answer_question(
            self, document: dict,
            classification: dict,
            explanation: dict,
            question: str,
            chat_history: list,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )

        messages = [
            {
                "role": "user",
                "content": (
                    f"Document type: "
                    f"{classification.get('document_type')}\n"
                    f"Jurisdiction: "
                    f"{classification.get('jurisdiction_name')}\n"
                    f"Summary: "
                    f"{explanation.get('summary', '')}\n\n"
                    f"Document text:\n"
                    f"{document.get('text', '')[:40000]}"
                )
            },
            {
                "role": "assistant",
                "content": (
                    "I have read and understood the document. "
                    "I am ready to answer questions about it "
                    "in plain language."
                )
            }
        ]

        for msg in chat_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        messages.append({
            "role": "user",
            "content": f"{spanish}\n{question}"
        })

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=messages
            )
            answer_text = response.content[0].text.strip()
            try:
                parsed = json.loads(answer_text)
                answer = parsed.get("answer", answer_text)
                confidence = parsed.get(
                    "confidence", "medium")
            except Exception:
                answer = answer_text
                confidence = "medium"
            return {
                "answer": answer,
                "confidence": confidence,
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang
            }
        except Exception as e:
            logger.error(
                "Anthropic call failed in %s: %s\n%s",
                self.__class__.__name__,
                repr(e),
                traceback.format_exc()
            )
            return {
                "answer": (
                    "Lo siento, no pude procesar su pregunta."
                    if lang == "es"
                    else "Sorry, I could not process "
                         "your question."),
                "confidence": "low",
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang,
            }
