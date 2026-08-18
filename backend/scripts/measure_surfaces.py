#!/usr/bin/env python3
"""Job 2 measurement: run each of the 7 prose surfaces against a
representative scenario (async agents) and count citation tokens that survive
the CitationFilter (registry loaded from prod court_rules)."""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.citation_filter import load_rule_citations_from_db, filter_citations_text  # noqa: E402
from src.memory.db import DatabaseManager  # noqa: E402

db = DatabaseManager()
load_rule_citations_from_db(db)

CITE_RE = re.compile(
    r"Fla\.\s*Stat\.\s*§\s*\d+(?:\.\d+)*(?:\(\w+\))*"
    r"|Fla\.\s*R\.\s*(?:Gen\.\s*Prac\.\s*&\s*Jud\.\s*Admin\.|Civ\.|Crim\.|Sm\.\s*Cl\.)\s*[A-Za-z. ]*?\d+(?:\.\d+)*",
    re.IGNORECASE,
)

SCENARIOS = [
    ("explainer (eviction)", "explainer"),
    ("small_claims", "small_claims"),
    ("criminal", "criminal"),
    ("discovery", "discovery"),
    ("wills_trusts", "wills_trusts"),
    ("property_casualty", "property_casualty"),
    ("chat", "chat"),
]

EVICTION_DOC = ("EVICTION SUMMONS/RESIDENTIAL\nCOUNTY COURT, MIAMI-DADE COUNTY\n"
                "Plaintiff: OAKWOOD APARTMENTS\nDefendant: JANE DOE\nYou are being sued. A complaint for "
                "eviction has been filed. YOU HAVE 5 BUSINESS DAYS to file a written response. If you fail "
                "to respond, a default judgment may be entered against you.\nThe plaintiff claims: "
                "nonpayment of rent for August 2026, $1,450.00, 3-day notice served July 10, 2026.")
SMALL_CLAIMS_DOC = ("STATEMENT OF CLAIM (Small Claims)\nPlaintiff: CARLOS MENDEZ\nDefendant: TINA'S "
                    "TAILORING LLC\nClaim: $4,200 unpaid invoice for alterations completed June 2026. "
                    "Plaintiff mailed a demand letter July 1, 2026. No response.")
CRIMINAL_DOC = ("NOTICE TO APPEAR\nState of Florida v. DARNELL W.\nCharge: petit theft "
                "(2nd degree misdemeanor), Fla. Stat. 812.014(3)(a)\nCourt date: September 14, 2026, "
                "9:00 AM, courtroom 4B.")
DISCOVERY_DOC = ("MOTION TO COMPEL DISCOVERY\nCase: 2026-CA-008123\nPlaintiff filed a Request for "
                 "Production 30 days ago. Defendant has not responded. Plaintiff seeks an order "
                 "compelling responses and sanctions.")
WILLS_DOC = ("PETITION FOR ADMINISTRATION\nIn Re: Estate of ROBERT L. THOMPSON, deceased July 2, 2026.\n"
             "Petitioner: SUSAN THOMPSON, surviving spouse. Decedent died intestate. Assets: homestead "
             "real property, one bank account ($38,000). Two adult children.")
PC_DOC = ("INSURANCE CLAIM DENIAL LETTER\nClaim No: HO-2026-881234\nInsured: MARIA GARCIA\nPeril: "
          "Hurricane wind damage to roof, July 2026.\nThis letter is to advise that coverage is denied. "
          "Reason: the reported loss occurred before the policy's effective date.")
CHAT_Q = ("I received a 5-day eviction summons in Florida. How much time do I have to respond, "
          "and what happens if I don't?")


def flatten(obj) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(flatten(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return " ".join(flatten(v) for v in obj)
    return str(obj)


async def run_agent(kind: str) -> str:
    if kind == "explainer":
        from src.agents.explainer import ExplainerAgent
        out = await ExplainerAgent().explain(EVICTION_DOC, "en")
        return flatten(out)
    if kind == "small_claims":
        from src.agents.small_claims import SmallClaimsExplainer
        out = await SmallClaimsExplainer().explain({"document_text": SMALL_CLAIMS_DOC}, "en")
        return flatten(out)
    if kind == "criminal":
        from src.agents.criminal_procedure import CriminalProcedureExplainer
        out = await CriminalProcedureExplainer().explain("petit theft", "misdemeanor", "notice to appear", "en")
        return flatten(out)
    if kind == "discovery":
        from src.agents.discovery_motion import DiscoveryMotionAnalyzer
        out = await DiscoveryMotionAnalyzer().analyze(DISCOVERY_DOC.encode(), "motion.txt", "en")
        return flatten(out)
    if kind == "wills_trusts":
        from src.agents.wills_trusts import WillsTrustsExplainer
        chunks = []
        async for chunk in WillsTrustsExplainer().explain(WILLS_DOC, "unknown", "en"):
            chunks.append(str(chunk))
        return " ".join(chunks)
    if kind == "property_casualty":
        from src.agents.property_casualty import PropertyCasualtyExplainer
        out = await PropertyCasualtyExplainer().explain(
            "homeowners_claim", {"document_text": PC_DOC}, "en")
        return flatten(out)
    if kind == "chat":
        from src.agents.chat_expert import ChatExpertAgent
        chunks = []
        async for chunk in ChatExpertAgent().chat("landlord_tenant", CHAT_Q, "measure-session", "en"):
            chunks.append(str(chunk))
        return " ".join(chunks)
    raise ValueError(kind)


async def main():
    for name, kind in SCENARIOS:
        try:
            raw = await run_agent(kind)
            emitted = CITE_RE.findall(raw)
            filtered = filter_citations_text(raw, f"measure:{kind}")
            kept = CITE_RE.findall(filtered)
            print(f"{name}: emitted={len(emitted)} kept={len(kept)} stripped={len(emitted)-len(kept)}")
            for c in emitted:
                print(f"   {'KEPT  ' if c in kept else 'STRIP '} {c}")
        except Exception as e:  # noqa: BLE001
            print(f"{name}: RUN FAILED: {type(e).__name__}: {e}")


asyncio.run(main())
