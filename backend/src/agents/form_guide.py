import json
import logging
import os
import traceback
from anthropic import AsyncAnthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a government and court form completion guide "
    "for LegalClear. You help ordinary people fill out legal "
    "and government forms correctly and completely. You explain "
    "each field in plain language. You know requirements for "
    "federal and state forms across all 50 US states. You flag "
    "common mistakes. You tell people exactly what to write. "
    "You never give legal advice. When the user's language is "
    "Spanish, respond entirely in Spanish. Return valid JSON "
    "only. No preamble. No markdown. JSON only."
)


class FormGuideAgent:

    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
            timeout=120.0,
        )
        self.model = "claude-sonnet-4-6"
        self._load_forms_library()

    def _load_forms_library(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "../data/forms_library.json")
        try:
            with open(path) as f:
                self.forms_library = json.load(f)
        except Exception:
            self.forms_library = {}

    async def guide(self, document: dict,
                    classification: dict,
                    lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )
        doc_type = classification.get("document_type", "")
        form_meta = self.forms_library.get(doc_type, {})
        official_url = form_meta.get("official_url", "")

        user_prompt = f"""Language: {lang}
{spanish}
Form type: {classification.get("document_type")}
Issuing agency: {classification.get("issuing_agency")}
Jurisdiction: {classification.get("jurisdiction_name")}
Filing deadline: {classification.get("filing_deadline")}
Official URL if known: {official_url}

Create a complete field-by-field completion guide.
Return JSON with exactly these fields:

form_overview: string explaining what this form is,
why people file it, what it does

before_you_start: list of strings for docs to gather

sections: list of section objects, each with:
  section_name, description, and fields list where
  each field has: field_name, field_number,
  plain_label, instructions, example,
  common_mistakes, required (boolean)

where_to_file: object with: methods (list),
address, online_url, fee, copies_needed, what_to_keep

after_filing: list of strings for next steps

deadline_warning: string if deadline is real, null if none

small_claims_hearing_tips: list of strings if small
claims document, null otherwise

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = await self.client.messages.create(
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
            return result
        except Exception as e:
            logger.error(
                "Anthropic call failed in %s: %s\n%s",
                self.__class__.__name__,
                repr(e),
                traceback.format_exc()
            )
            return {"error": True, "message": "An error occurred. Please try again.",
                    "disclaimer": get_disclaimer(
                        lang, "standard")}

    async def answer_form_question(
            self, document: dict,
            classification: dict,
            guide: dict, question: str,
            chat_history: list,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )
        context = (
            f"Form type: "
            f"{classification.get('document_type')}\n"
            f"Jurisdiction: "
            f"{classification.get('jurisdiction_name')}\n"
            f"Form overview: "
            f"{guide.get('form_overview', '')}\n\n"
            f"Document text:\n"
            f"{document.get('text', '')[:30000]}"
        )
        messages = [
            {"role": "user", "content": context},
            {"role": "assistant",
             "content": (
                 "I have reviewed this form and its "
                 "completion guide. Ready to answer "
                 "questions about how to fill it out.")}
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
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=messages
            )
            answer = response.content[0].text.strip()
            return {
                "answer": answer,
                "confidence": "high",
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
                    "No pude procesar su pregunta."
                    if lang == "es"
                    else "Could not process your question."),
                "confidence": "low",
                "disclaimer": get_disclaimer(lang, "short"),
                "language": lang,
            }
