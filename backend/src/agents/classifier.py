import json
from anthropic import Anthropic
from src.core.config import settings

SYSTEM_PROMPT = (
    "You are a legal document classification expert. "
    "Your only job is to analyze legal documents and return "
    "precise structured metadata about what they are. "
    "You are highly accurate. You never guess. If uncertain "
    "about any field, return \"unknown\". You always return "
    "valid JSON and nothing else. "
    "No preamble. No explanation. No markdown. JSON only."
)

VALID_CATEGORIES = [
    "contract", "government_form", "court_filing", "notice",
    "agreement", "will_estate", "employment", "real_estate",
    "financial", "criminal_charge", "criminal_summons",
    "plea_agreement", "restraining_order",
    "expungement_petition", "small_claims_complaint",
    "small_claims_response", "small_claims_judgment", "other"
]


class ClassifierAgent:

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
            timeout=60.0,
        )
        self.model = "claude-haiku-4-5-20251001"

    async def classify(self, document: dict) -> dict:
        text_sample = document.get("text", "")[:24000]

        user_prompt = f"""Analyze this legal document and
return JSON with exactly these fields:

document_category: one of exactly these values:
{", ".join(VALID_CATEGORIES)}

document_type: specific type string e.g.
"residential_lease", "IRS_1040",
"small_claims_complaint_florida"

jurisdiction_type: one of: federal, state, local, unknown

jurisdiction_name: state name if state/local,
"federal" if federal, "unknown" if cannot determine

issuing_agency: e.g. "IRS", "USCIS",
"Florida Courts", "unknown"

parties: list of up to 4 party names found

key_dates: list of objects each with label, date,
importance fields

filing_deadline: date string if found, "none" if not
applicable, "unknown" if unclear

estimated_complexity: one of: simple, moderate, complex

detected_language: one of: en, es, unknown

red_flag_preview: list of up to 3 brief strings noting
immediate concerns

confidence: float 0.0 to 1.0

Document text:
{text_sample}"""

        for attempt in range(2):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=[{
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {
                            "type": "ephemeral"}
                    }],
                    messages=[{
                        "role": "user",
                        "content": (
                            "Return ONLY a JSON object. "
                            "No other text. " + user_prompt
                            if attempt > 0
                            else user_prompt)
                    }]
                )
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                return json.loads(raw)
            except Exception as e:
                print(f"Exception calling Anthropic: {e}")
                if attempt == 1:
                    return self._default()
        return self._default()

    def _default(self) -> dict:
        return {
            "document_category": "unknown",
            "document_type": "unknown",
            "jurisdiction_type": "unknown",
            "jurisdiction_name": "unknown",
            "issuing_agency": "unknown",
            "parties": [],
            "key_dates": [],
            "filing_deadline": "unknown",
            "estimated_complexity": "simple",
            "detected_language": "en",
            "red_flag_preview": [],
            "confidence": 0.0
        }

    def get_price_tier(self, document: dict) -> dict:
        tokens = document.get("token_estimate", 0)
        if tokens < 4000:
            return {"tier": "small", "price_usd": 5,
                    "label": "Short document (under 5 pages)"}
        elif tokens <= 12000:
            return {"tier": "medium", "price_usd": 10,
                    "label": "Standard document (5-15 pages)"}
        else:
            return {"tier": "large", "price_usd": 15,
                    "label": "Complex document (15+ pages)"}
