import json
import logging
import traceback
from anthropic import Anthropic
from src.core.config import settings
from src.core.disclaimer import get_disclaimer

logger = logging.getLogger(__name__)

GUIDE_SYSTEM_PROMPT = (
    "You are an expungement petition guide for LegalClear. "
    "You help people understand the expungement process and "
    "fill out expungement petitions correctly. Expungement "
    "seals or clears a criminal record, giving people a fresh "
    "start in employment, housing, and professional licensing. "
    "You explain every step clearly in plain language. You know "
    "expungement laws for all 50 US states. You never give "
    "legal advice. When the user's language is Spanish, respond "
    "entirely in Spanish. Return valid JSON only. "
    "No preamble. No markdown. JSON only."
)

ELIGIBILITY_SYSTEM_PROMPT = (
    "You are a preliminary expungement eligibility assessor "
    "for LegalClear. You provide general eligibility estimates "
    "based on jurisdiction, offense type, and time elapsed. "
    "You are always clear this is preliminary only and not "
    "legal advice. Individual circumstances vary. Always "
    "recommend verifying with the court. Return valid JSON "
    "only. No preamble. No markdown. JSON only."
)


class ExpungementAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
            timeout=120.0,
        )
        self.guide_model = "claude-sonnet-4-6"
        self.eligibility_model = "claude-haiku-4-5-20251001"

    async def guide(self, document: dict,
                    classification: dict,
                    lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish. "
            "All JSON values must be in Spanish."
            if lang == "es" else ""
        )
        jurisdiction = classification.get(
            "jurisdiction_name", "unknown")

        user_prompt = f"""Language: {lang}
{spanish}
Jurisdiction: {jurisdiction}
Document type: expungement_petition

Return JSON with:

what_is_expungement: plain language explanation of what
expungement does and why it matters

eligibility_overview: general criteria for {jurisdiction},
always note eligibility varies by case

before_you_start: list of documents and info to gather

steps: list of step objects each with:
  step_number, title, instructions, tips,
  estimated_time, cost

form_fields: list of field objects each with:
  field_name, plain_label, instructions,
  example, common_mistakes, required

where_to_file: object with: court_type, methods,
address_note, online_url, fee, fee_waiver_note

after_filing: list of strings

what_changes_after: list of concrete improvements
after successful expungement

what_does_not_change: list of important limitations

free_resources: list of objects each with:
  label, url, description
Always include expungement.com and lawhelp.org

Document text:
{document.get("text", "")[:80000]}"""

        try:
            response = self.client.messages.create(
                model=self.guide_model,
                max_tokens=8192,
                system=[{
                    "type": "text",
                    "text": GUIDE_SYSTEM_PROMPT,
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
            return {"error": True, "message": str(e),
                    "exception_type": type(e).__name__,
                    "disclaimer": get_disclaimer(
                        lang, "standard")}

    async def check_eligibility(
            self, jurisdiction: str,
            offense_description: str,
            years_since_offense: int,
            lang: str = "en") -> dict:
        spanish = (
            "Respond entirely in Spanish."
            if lang == "es" else ""
        )

        user_prompt = f"""Language: {lang}
{spanish}
Jurisdiction: {jurisdiction}
Offense: {offense_description}
Years since offense: {years_since_offense}

Return JSON with:
likely_eligible: boolean
confidence: one of: high, medium, low
reasoning: plain language explanation
key_factors: list of strings
next_steps: list of strings
disclaimer: always include that this is preliminary
only and not legal advice"""

        try:
            response = self.client.messages.create(
                model=self.eligibility_model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": ELIGIBILITY_SYSTEM_PROMPT,
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
            return json.loads(raw)
        except Exception as e:
            logger.error(
                "Anthropic call failed in %s: %s\n%s",
                self.__class__.__name__,
                repr(e),
                traceback.format_exc()
            )
            return {
                "likely_eligible": False,
                "confidence": "low",
                "reasoning": (
                    "Could not assess eligibility."),
                "key_factors": [],
                "next_steps": [
                    "Contact your local legal aid office",
                    "Visit https://www.lawhelp.org"
                ],
                "disclaimer": get_disclaimer(
                    lang, "standard"),
                "error": str(e),
                "exception_type": type(e).__name__
            }
