"""
Phase 8 — Legal information layer (formerly UPL compliance).

The product provides EDUCATED LEGAL INFORMATION, not a wall of disclaimers.
The LLM explains what the law says, what the document means, and what the
person's options are. Every output ends by directing the user to consult a
licensed attorney before acting.

Pattern: "Here's what's happening. Here's what you should know. Here's what
you can do about it. But confirm with an attorney before you act."

Guardrails:
  - Outputs MUST end with attorney referral.
  - Criminal/expungement: explain the charges/procedure, then direct to
    public defender or criminal defense attorney.
  - Urgent deadlines (<72h): surface the urgency, explain consequences of
    missing it, direct to immediate attorney help.
  - When genuinely uncertain: say so, then direct to attorney.
  - The disclaimer is a nudge at the end, not a wall that blocks help.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ── Disclaimer texts ──────────────────────────────────────────────────────────
# Pattern: acknowledge this is information → direct to attorney for action.

_DISCLAIMERS: dict[str, dict[str, str]] = {
    "standard": {
        "en": (
            "This is legal information from an automated tool, not a substitute "
            "for a licensed attorney. Before filing anything or acting on a "
            "deadline, confirm with a Florida attorney. Free or low-cost help: "
            "floridalawhelp.org | Florida Bar Lawyer Referral: floridabar.org/public/lrs "
            "($25 for 30-minute consultation)."
        ),
        "es": (
            "Esta es información legal generada por una herramienta automatizada, "
            "no un sustituto de un abogado autorizado. Antes de presentar algo o "
            "actuar sobre un plazo, confirme con un abogado de Florida. Ayuda "
            "gratuita o de bajo costo: floridalawhelp.org"
        ),
    },
    "urgent": {
        "en": (
            "A legal deadline is approaching. The consequences of missing it "
            "may be severe. Seek help from a licensed Florida attorney immediately. "
            "Free help may be available at floridalawhelp.org."
        ),
        "es": (
            "Se acerca un plazo legal. Las consecuencias de no cumplirlo pueden "
            "ser graves. Busque ayuda de un abogado autorizado de Florida de "
            "inmediato. Puede haber ayuda gratuita en floridalawhelp.org."
        ),
    },
    "criminal": {
        "en": (
            "This involves a criminal matter. You have the right to an attorney. "
            "If you cannot afford one, a public defender may be appointed — "
            "contact the public defender's office in your county immediately. "
            "Do not rely solely on automated information for criminal cases."
        ),
        "es": (
            "Esto involucra un asunto penal. Usted tiene derecho a un abogado. "
            "Si no puede pagar uno, se le puede asignar un defensor público — "
            "comuníquese con la oficina del defensor público de su condado de "
            "inmediato. No confíe únicamente en información automatizada para "
            "casos penales."
        ),
    },
}

ATTORNEY_REFERRAL_LINKS = {
    "en": [
        {"label": "Find free legal help in Florida",
         "url": "https://www.floridalawhelp.org"},
        {"label": "Florida Bar Lawyer Referral Service ($25/30min)",
         "url": "/attorney-referral"},
        {"label": "Florida Courts Self-Help Information",
         "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/"
                "Family-Courts/Self-Help-Information"},
    ],
    "es": [
        {"label": "Ayuda legal gratuita en Florida",
         "url": "https://www.floridalawhelp.org"},
        {"label": "Servicio de referencia de abogados del Colegio de Florida",
         "url": "/attorney-referral"},
    ],
}


def apply_disclaimer(output: dict[str, Any], lang: str = "en",
                     level: str = "standard") -> dict[str, Any]:
    """Add disclaimer + attorney referral links to any output dict."""
    _lang = lang if lang in ("en", "es") else "en"
    _level = level if level in _DISCLAIMERS else "standard"
    return {
        **output,
        "disclaimer": _DISCLAIMERS[_level][_lang],
        "attorney_referral_links": ATTORNEY_REFERRAL_LINKS.get(lang, ATTORNEY_REFERRAL_LINKS["en"]),
        "language": lang,
    }


# ── Escalation triggers ───────────────────────────────────────────────────────

FATAL_CONFIDENCE_THRESHOLD = 0.90
URGENT_HOURS = 72


@dataclass
class EscalationResult:
    should_escalate: bool
    reasons: list[str] = field(default_factory=list)
    urgency: str = "standard"
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
    """Evaluate escalation triggers and return consolidated result.

    Triggers:
    1. Fatal severity + extraction confidence < 0.90
    2. Any deadline within 72 hours
    3. Document type is 'unknown'
    4. Matter involves minor children
    5. Criminal or expungement-related
    """
    now = now or datetime.now(tz=UTC)
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
            "Criminal matter detected. The user should be informed of the "
            "charges and procedure, then directed to the public defender "
            "or a criminal defense attorney immediately."
        )
        urgency = "immediate"
        disclaimer_level = "criminal"

    # Trigger 3: unknown document type
    if doc_type == "unknown" or not doc_type:
        reasons.append(
            "Document type uncertain. Best-effort analysis should still be "
            "provided, with a strong recommendation to verify with an attorney."
        )
        urgency = max(urgency, "high", key=_urgency_rank)

    # Trigger 4: minor children
    if involves_children:
        reasons.append(
            "Minor children are involved. The analysis should cover custody, "
            "time-sharing, and support considerations, then direct to an "
            "attorney since children's cases have additional obligations."
        )
        urgency = max(urgency, "high", key=_urgency_rank)

    # Deadline-based triggers
    for dl in deadlines:
        severity = dl.get("severity", "")
        confidence = float(dl.get("confidence", 1.0))
        due_date_str = dl.get("due_date")

        if severity == "fatal" and confidence < FATAL_CONFIDENCE_THRESHOLD:
            reasons.append(
                f"Fatal deadline ({dl.get('label', 'unknown')}) with "
                f"{confidence:.0%} confidence. Explain the deadline and its "
                f"consequences, then direct to attorney for verification."
            )
            urgency = max(urgency, "high", key=_urgency_rank)

        if due_date_str:
            try:
                due_dt = datetime(
                    *[int(x) for x in due_date_str.split("-")],
                    17, 0, 0, tzinfo=UTC
                )
                hours_remaining = (due_dt - now).total_seconds() / 3600
                if 0 < hours_remaining <= URGENT_HOURS:
                    reasons.append(
                        f"DEADLINE WITHIN {int(hours_remaining)} HOURS: "
                        f"{dl.get('label', 'unknown')}. Surface urgency, "
                        f"explain consequences of missing it."
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
    doc_type = cls.get("document_type") or ""
    notes = (cls.get("notes") or "").lower()
    if "children" in doc_type or "minor" in notes or "child" in notes:
        return True
    if cls.get("document_type") == "family_law_petition":
        return True
    return any("child" in (dl.get("label") or "").lower() for dl in deadlines)


def _referral_text(reasons: list[str], urgency: str, lang: str) -> str:
    if not reasons:
        return ""
    if lang == "es":
        if urgency == "immediate":
            return (
                "Busque asesoramiento legal de inmediato. Puede haber ayuda "
                "gratuita en floridalawhelp.org."
            )
        return (
            "Confirme esta información con un abogado autorizado de Florida "
            "antes de actuar. Ayuda gratuita: floridalawhelp.org."
        )
    if urgency == "immediate":
        return (
            "Seek legal help immediately. Free help may be available at "
            "floridalawhelp.org."
        )
    return (
        "Confirm this information with a licensed Florida attorney before "
        "acting. Free help: floridalawhelp.org."
    )


# ── Output guidance (replaces the old UPL_RISK_PHRASES block) ─────────────────
#
# The old approach blocked directive language ("you should", "I recommend").
# The new approach lets the LLM give educated answers and ensures every
# output directs to an attorney at the end.
#
# Phrases that should trigger an attorney nudge (not a block — a reminder
# that the system adds to the end of the output):
#
#   "you should"  → append: "An attorney can confirm this is right for your case."
#   "you must"    → append: "Confirm this requirement with an attorney."
#   "you need to" → append: "Verify the exact steps with an attorney."

ATTORNEY_NUDGE_PHRASES = [
    ("you should", "An attorney can confirm this is the right course for your situation."),
    ("you must", "Confirm this legal requirement with an attorney before acting."),
    ("you need to", "Verify the exact steps and deadlines with an attorney."),
    ("i recommend", "A licensed attorney can give you personalized advice for your case."),
    ("your best option", "Discuss your options with an attorney before deciding."),
    ("the best course", "An attorney can help you evaluate the best course for your situation."),
    ("do not", "Confirm with an attorney that this restriction applies to your case."),
    ("never", "Verify with an attorney before relying on this as an absolute rule."),
]


def nudge_for_attorney(text: str) -> str:
    """If the text contains directive language, append an attorney nudge.

    This replaces the old UPL_RISK_PHRASES blocking approach. Instead of
    preventing the LLM from helping, we let it give educated answers and
    add a contextual nudge at the end.
    """
    text_lower = text.lower()
    nudges_seen: set[str] = set()
    for phrase, nudge in ATTORNEY_NUDGE_PHRASES:
        if phrase in text_lower and nudge not in nudges_seen:
            nudges_seen.add(nudge)

    if nudges_seen:
        return text + "\n\n" + " ".join(sorted(nudges_seen))

    return text


# Backward compatibility — re-export audit function for tests
def audit_output_for_upl(text: str) -> list[str]:
    """Return phrases in the output that may need an attorney nudge."""
    text_lower = text.lower()
    return [phrase for phrase, _ in ATTORNEY_NUDGE_PHRASES if phrase in text_lower]


def apply_upl_guardrails(text: str, lang: str = "en") -> str:
    """Apply attorney-nudge guardrails to analysis text.

    Scans for directive language and appends contextual attorney nudges.
    No longer blocks — adds context.
    """
    return nudge_for_attorney(text)
