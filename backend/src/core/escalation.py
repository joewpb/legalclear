import json
import logging
import os

from .disclaimer import get_disclaimer

logger = logging.getLogger(__name__)


def _load_jurisdictions():
    path = os.path.join(
        os.path.dirname(__file__),
        "../data/jurisdictions.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load jurisdictions: %s", e)
        return {}


_JURISDICTIONS = _load_jurisdictions()

_STANDARD = [
    "contract", "agreement", "real_estate", "employment",
    "financial", "will_estate", "notice", "other"
]
_ELEVATED = [
    "government_form", "court_filing",
    "small_claims_complaint", "small_claims_response",
    "small_claims_judgment", "expungement_petition"
]
_CRIMINAL = [
    "criminal_charge", "criminal_summons",
    "restraining_order"
]

_LINKS_EN = [
    {"label": "Find free legal aid",
     "url": "https://www.lawhelp.org"},
    {"label": "Find your public defender",
     "url": "https://www.nacdl.org/Landing/PublicDefenders"},
    {"label": "Court self-help center",
     "url": "https://www.ncsc.org/topics/access-and-fairness/"
             "self-represented-litigants/resource-guide"}
]

_LINKS_ES = [
    {"label": "Encuentre ayuda legal gratuita",
     "url": "https://www.lawhelp.org"},
    {"label": "Encuentre su defensor publico",
     "url": "https://www.nacdl.org/Landing/PublicDefenders"},
    {"label": "Centro de autoayuda del tribunal",
     "url": "https://www.ncsc.org/topics/access-and-fairness/"
             "self-represented-litigants/resource-guide"}
]


class EscalationRouter:

    def route(self, classification: dict,
              lang: str = "en") -> dict:
        category = classification.get(
            "document_category", "other")
        jurisdiction = classification.get(
            "jurisdiction_name", "unknown")
        links = _LINKS_ES if lang == "es" else _LINKS_EN
        jur_data = _JURISDICTIONS.get(jurisdiction, {})
        if jur_data.get("legal_aid_url"):
            links = links + [{
                "label": ("Ayuda legal en su estado"
                          if lang == "es"
                          else "Legal aid in your state"),
                "url": jur_data["legal_aid_url"]
            }]

        if category in _STANDARD:
            return {"disclaimer_level": "standard",
                    "show_attorney_warning": False,
                    "show_public_defender_info": False,
                    "pre_analysis_warning": None,
                    "resource_links": links,
                    "escalation_color": "green"}
        if category in _ELEVATED:
            return {"disclaimer_level": "standard",
                    "show_attorney_warning": True,
                    "show_public_defender_info": False,
                    "pre_analysis_warning": None,
                    "resource_links": links,
                    "escalation_color": "yellow"}
        if category in _CRIMINAL:
            return {"disclaimer_level": "criminal",
                    "show_attorney_warning": True,
                    "show_public_defender_info": True,
                    "pre_analysis_warning": get_disclaimer(
                        lang, "criminal"),
                    "resource_links": links,
                    "escalation_color": "red"}
        if category == "plea_agreement":
            return {"disclaimer_level": "plea",
                    "show_attorney_warning": True,
                    "show_public_defender_info": True,
                    "pre_analysis_warning": get_disclaimer(
                        lang, "plea"),
                    "resource_links": links,
                    "escalation_color": "red"}
        return {"disclaimer_level": "standard",
                "show_attorney_warning": False,
                "show_public_defender_info": False,
                "pre_analysis_warning": None,
                "resource_links": links,
                "escalation_color": "green"}
