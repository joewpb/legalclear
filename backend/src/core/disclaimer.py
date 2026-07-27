"""
Phase 8 — Legal information disclaimers.

Every output ends with a disclaimer that directs the user to consult
an attorney. The disclaimer is a nudge, not a wall.

Pattern: "This is legal information. [Educated analysis above].
Confirm with a licensed Florida attorney before acting."
"""

DISCLAIMER_EN = (
    "This is legal information from an automated tool, not a substitute "
    "for a licensed attorney. The analysis above explains what the law "
    "says — but every case is different. Confirm this with a Florida "
    "attorney before filing anything or acting on a deadline. Free or "
    "low-cost help: floridalawhelp.org | Florida Bar Lawyer Referral: "
    "floridabar.org/public/lrs ($25 for 30-minute consultation)."
)

DISCLAIMER_ES = (
    "Esta es información legal generada por una herramienta automatizada, "
    "no un sustituto de un abogado autorizado. El análisis anterior explica "
    "lo que dice la ley — pero cada caso es diferente. Confirme esto con "
    "un abogado de Florida antes de presentar algo o actuar sobre un plazo. "
    "Ayuda gratuita o de bajo costo: floridalawhelp.org"
)

SHORT_DISCLAIMER_EN = (
    "Confirm this with a licensed attorney before acting. Free help: "
    "floridalawhelp.org."
)

SHORT_DISCLAIMER_ES = (
    "Confirme esto con un abogado antes de actuar. Ayuda gratuita: "
    "floridalawhelp.org."
)

CRIMINAL_WARNING_EN = (
    "This involves a criminal matter. You have the right to an attorney. "
    "If you cannot afford one, a public defender may be appointed — contact "
    "the public defender's office in your county immediately. Do not rely "
    "solely on automated information for criminal cases. The analysis above "
    "explains what this document says, but a criminal defense attorney is "
    "the only person who can properly advise you on next steps."
)

CRIMINAL_WARNING_ES = (
    "Esto involucra un asunto penal. Usted tiene derecho a un abogado. "
    "Si no puede pagar uno, se le puede asignar un defensor público — "
    "comuníquese con la oficina del defensor público de su condado de "
    "inmediato. No confíe únicamente en información automatizada para "
    "casos penales. El análisis anterior explica lo que dice este "
    "documento, pero un abogado penalista es la única persona que puede "
    "asesorarlo adecuadamente sobre los próximos pasos."
)

PLEA_WARNING_EN = (
    "WARNING: This is a plea agreement. Signing this document waives "
    "important legal rights that cannot be recovered. Do NOT sign without "
    "first speaking to an attorney or public defender. This is the single "
    "most important action you can take right now. Call the public defender "
    "immediately at your county courthouse."
)

PLEA_WARNING_ES = (
    "ADVERTENCIA: Este es un acuerdo de culpabilidad. Firmar este "
    "documento renuncia a derechos legales importantes que no se pueden "
    "recuperar. NO firme sin antes hablar con un abogado o defensor "
    "público. Llame al defensor público de inmediato en el tribunal de "
    "su condado."
)


def get_disclaimer(lang: str, level: str = "standard") -> str:
    lang = "es" if lang == "es" else "en"
    if level == "standard":
        return DISCLAIMER_ES if lang == "es" else DISCLAIMER_EN
    if level == "short":
        return SHORT_DISCLAIMER_ES if lang == "es" else SHORT_DISCLAIMER_EN
    if level == "criminal":
        return CRIMINAL_WARNING_ES if lang == "es" else CRIMINAL_WARNING_EN
    if level == "plea":
        return PLEA_WARNING_ES if lang == "es" else PLEA_WARNING_EN
    return DISCLAIMER_EN
