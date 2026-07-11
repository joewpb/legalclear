"""Phase 8 — UPL compliance layer.

Enforces two invariants across every user-facing output:
  1. Every output carries a disclaimer (legal information ≠ legal advice).
  2. High-stakes situations escalate to attorney referral rather than guess.

Guardrails:
  - Never weaken or remove the disclaimer for UX reasons.
  - When in doubt, escalate or decline — do not guess.
  - The LLM explains consequences; it never selects a course of action.

NOTE: Disclaimer text must be reviewed against the Terms of Service
(parallel workstream, Joe + attorneys) before public launch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── Disclaimer texts ──────────────────────────────────────────────────────────

_DISCLAIMERS: dict[str, dict[str, str]] = {
    "standard": {
        "en": (
            "This is legal information, not legal advice. "
            "LegalClear helps you understand court documents and deadlines. "
            "It is not a substitute for advice from a licensed Florida attorney. "
            "Deadlines and legal consequences vary by case — this information "
            "may not reflect all factors relevant to your situation. "
            "If a deadline is approaching or you have questions, consult a "
            "licensed Florida attorney immediately."
        ),
        "es": (
            "Esto es información legal, no asesoramiento legal. "
            "LegalClear le ayuda a comprender documentos y plazos judiciales. "
            "No reemplaza el consejo de un abogado autorizado de Florida. "
            "Los plazos y consecuencias legales varían según el caso; esta "
            "información puede no reflejar todos los factores relevantes a su situación. "
            "Si se acerca un plazo o tiene preguntas, consulte de inmediato a un "
            "abogado autorizado de Florida."
        ),
    },
    "urgent": {
        "en": (
            "IMPORTANT: A legal deadline may be approaching soon. "
            "This is legal information, not legal advice. "
            "Please consult a licensed Florida attorney immediately. "
            "Free or low-cost legal help may be available at lawhelp.org."
        ),
        "es": (
            "IMPORTANTE: Es posible que se acerque pronto un plazo legal. "
            "Esto es información legal, no asesoramiento legal. "
            "Consulte de inmediato a un abogado autorizado de Florida. "
            "Puede haber ayuda legal gratuita o de bajo costo en lawhelp.org."
        ),
    },
    "criminal": {
        "en": (
            "IMPORTANT: This document appears to involve a criminal matter. "
            "LegalClear does not analyze criminal cases. "
            "You have the right to an attorney. If you cannot afford one, "
            "a public defender may be appointed. Contact the public "
            "defender's office or a criminal defense attorney immediately."
        ),
        "es": (
            "IMPORTANTE: Este documento parece involucrar un asunto penal. "
            "LegalClear no analiza casos penales. "
            "Usted tiene derecho a un abogado. Si no puede pagar uno, "
            "se le puede asignar un defensor público. Comuníquese de inmediato "
            "con la oficina del defensor público o un abogado penalista."
        ),
    },
}

ATTORNEY_REFERRAL_LINKS = {
    "en": [
        {"label": "Find free legal help in Florida",
         "url": "https://www.floridalawhelp.org"},
        {"label": "Florida Bar Lawyer Referral Service",
         "url": "https://www.floridabar.org/public/lrs/"},
        {"label": "Florida Courts Self-Help",
         "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/"
                "Family-Courts/Self-Help-Information"},
    ],
    "es": [
        {"label": "Ayuda legal gratuita en Florida",
         "url": "https://www.floridalawhelp.org"},
        {"label": "Servicio de referencia de abogados del Colegio de Florida",
         "url": "https://www.floridabar.org/public/lrs/"},
    ],
}


def get_disclaimer(level: str = "standard", lang: str = "en") -> str:
    """Return an escalation-tier disclaimer: ``standard`` | ``urgent`` | ``criminal``.

    This is the UPL/escalation vocabulary, keyed by severity tier and consumed
    by ``check_escalation`` (which sets ``disclaimer_level`` to one of these
    tiers). It is intentionally distinct from ``src/core/disclaimer.py``, which
    holds the agent-facing disclaimer copy (``standard|short|criminal|plea``)
    imported by the explainer agents.

    Do NOT re-add a one-arg ``get_disclaimer(lang)`` here: a second definition
    shadows this one and breaks ``apply_disclaimer`` plus the test suite.
    """
    lang = lang if lang in ("en", "es") else "en"
    level = level if level in _DISCLAIMERS else "standard"
    return _DISCLAIMERS[level][lang]


def apply_disclaimer(output: dict[str, Any], lang: str = "en",
                     level: str = "standard") -> dict[str, Any]:
    """Add a disclaimer field to any output dict. Never removes existing fields."""
    return {**output, "disclaimer": get_disclaimer(level, lang), "language": lang}


# ── Escalation triggers ───────────────────────────────────────────────────────

FATAL_CONFIDENCE_THRESHOLD = 0.90   # Phase 4 spec
URGENT_HOURS = 72                   # Phase 8 spec


@dataclass
class EscalationResult:
    should_escalate: bool
    reasons: list[str] = field(default_factory=list)
    urgency: str = "standard"       # "immediate" | "high" | "standard"
    disclaimer_level: str = "standard"
    attorney_referral_links: list[dict] = field(default_factory=list)
    referral_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_escalate": self.should_escalate,
            "reasons": self.reasons,
            "urgency": self.urgency,
            "disclaimer_level": self.disclaimer_level,
            "attorney_referral_links": self.attorney_referral_links,
            "referral_text": self.referral_text,
        }


def check_escalation(
    classification: dict[str, Any] | None,
    deadlines: list[dict[str, Any]],
    now: datetime | None = None,
    lang: str = "en",
) -> EscalationResult:
    """Evaluate all 5 escalation triggers and return a consolidated result.

    Triggers (from Phase 8 spec):
    1. Fatal severity + extraction confidence < 0.90
    2. Any deadline within 72 hours
    3. Document type is 'unknown'
    4. Matter involves minor children
    5. Criminal or expungement-related

    The result is written to documents.escalation by the caller.
    """
    now = now or datetime.now(tz=timezone.utc)
    reasons: list[str] = []
    urgency = "standard"
    disclaimer_level = "standard"

    cls = classification or {}
    doc_type = cls.get("document_type", "unknown")
    is_criminal = bool(cls.get("is_criminal", False))
    is_expungement = bool(cls.get("is_expungement", False))
    involves_children = _involves_minor_children(cls, deadlines)

    # Trigger 5: criminal or expungement
    if is_criminal or is_expungement:
        reasons.append(
            "This document involves a criminal matter or expungement. "
            "LegalClear does not analyze criminal cases."
        )
        urgency = "immediate"
        disclaimer_level = "criminal"

    # Trigger 3: unknown document type
    if doc_type == "unknown" or not doc_type:
        reasons.append(
            "The document type could not be determined. "
            "A licensed attorney can review the document and identify "
            "the applicable deadlines and procedures."
        )
        urgency = max(urgency, "high", key=_urgency_rank)

    # Trigger 4: minor children
    if involves_children:
        reasons.append(
            "This matter appears to involve minor children. "
            "Cases involving children carry additional legal obligations "
            "that vary by circumstance — an attorney can identify them."
        )
        urgency = max(urgency, "high", key=_urgency_rank)

    # Deadline-based triggers
    for dl in deadlines:
        severity = dl.get("severity", "")
        confidence = float(dl.get("confidence", 1.0))
        due_date_str = dl.get("due_date")

        # Trigger 1: fatal + low confidence
        if severity == "fatal" and confidence < FATAL_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"A fatal deadline ({dl.get('label', 'unknown')}) was identified "
                f"with only {confidence:.0%} extraction confidence. "
                f"An attorney can verify the exact deadline."
            )
            urgency = max(urgency, "high", key=_urgency_rank)

        # Trigger 2: within 72 hours
        if due_date_str:
            try:
                due_dt = datetime(
                    *[int(x) for x in due_date_str.split("-")],
                    17, 0, 0, tzinfo=timezone.utc
                )
                hours_remaining = (due_dt - now).total_seconds() / 3600
                if 0 < hours_remaining <= URGENT_HOURS:
                    reasons.append(
                        f"A deadline ({dl.get('label', 'unknown')}) is within "
                        f"{int(hours_remaining)} hours. Seek legal help immediately."
                    )
                    urgency = "immediate"
                    disclaimer_level = "urgent"
            except (ValueError, TypeError):
                pass

    should_escalate = bool(reasons)

    referral_text = _referral_text(reasons, urgency, lang)

    return EscalationResult(
        should_escalate=should_escalate,
        reasons=reasons,
        urgency=urgency,
        disclaimer_level=disclaimer_level,
        attorney_referral_links=ATTORNEY_REFERRAL_LINKS.get(lang, ATTORNEY_REFERRAL_LINKS["en"]),
        referral_text=referral_text,
    )


def _urgency_rank(u: str) -> int:
    return {"standard": 0, "high": 1, "immediate": 2}.get(u, 0)


def _involves_minor_children(cls: dict, deadlines: list[dict]) -> bool:
    """Detect minor-child involvement from classification and deadline labels."""
    doc_type = cls.get("document_type") or ""
    notes = (cls.get("notes") or "").lower()
    if "children" in doc_type or "minor" in notes or "child" in notes:
        return True
    if cls.get("document_type") == "family_law_petition":
        # Family law petitions may involve children — surface for review
        return True
    for dl in deadlines:
        if "child" in (dl.get("label") or "").lower():
            return True
    return False


def _referral_text(reasons: list[str], urgency: str, lang: str) -> str:
    if not reasons:
        return ""
    if lang == "es":
        if urgency == "immediate":
            return "Busque asesoramiento legal de inmediato. Puede haber ayuda gratuita en floridalawhelp.org."
        return "Considere consultar a un abogado autorizado de Florida. Puede haber ayuda gratuita en floridalawhelp.org."
    if urgency == "immediate":
        return "Seek legal help immediately. Free help may be available at floridalawhelp.org."
    return "Consider consulting a licensed Florida attorney. Free help may be available at floridalawhelp.org."


# ── Output audit ──────────────────────────────────────────────────────────────

# Patterns that indicate legal advice rather than legal information
# (for use in testing and review — not a runtime filter)
UPL_RISK_PHRASES = [
    "you should",
    "you must",
    "you need to",
    "i recommend",
    "i advise",
    "my advice",
    "you ought to",
    "the best course",
    "your best option",
    "you are required to",   # OK in statute quotes but flag for review
    "do not",                # directive — flag for review
    "never",                 # directive — flag for review
]


def audit_output_for_upl(text: str) -> list[str]:
    """Return a list of phrases that may indicate legal advice rather than information.

    Used during the attorney review process (Task 5) to flag specific wording.
    This is not a runtime block — it surfaces phrases for human review.
    """
    found = []
    text_lower = text.lower()
    for phrase in UPL_RISK_PHRASES:
        if phrase in text_lower:
            found.append(phrase)
    return found


def apply_upl_guardrails(text: str, lang: str = "en") -> str:
    """Apply UPL guardrails to analysis text.

    Scans for phrases that may constitute legal advice and appends
    the standard disclaimer. Returns the safe text.
    """
    flagged = audit_output_for_upl(text)
    if flagged:
        from src.core.disclaimer import get_disclaimer as _get

        disclaimer = _get(lang)
        return f"{text}\n\n⚠️ {disclaimer}"
    return text
