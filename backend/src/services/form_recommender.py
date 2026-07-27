"""
Form Recommender — deterministic decision tree → case type → Supabase forms.

Ported from the LegalClear GitHub repo's scripts/form_finder.py.
No LLM calls — pure branching logic. Returns form metadata from the
Supabase court_forms table paired with plain-English explanations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Plain-English Form Explanations ───────────────────────────
# Mirrors form_finder.py FORM_EXPLANATIONS, extended for Supabase forms.
FORM_EXPLANATIONS: dict[str, str] = {
    # Divorce
    "12.901(b)(1)": "Petition to start a divorce when you have minor children. Tells the court who you are, basic facts about your marriage, and what you want decided about kids, money, and property.",
    "12.901(b)(2)": "Petition to start a divorce when you have NO minor children. Simpler — covers who you are, what you own and owe, and that you want a divorce.",
    "12.901(a)": "Simplified Dissolution — the fastest, cheapest divorce. Use ONLY if both agree on everything, have no minor children, neither is pregnant, and both waive trial/appeal rights.",
    "12.902(b)": "Short financial affidavit. Use if your income is UNDER $50,000/year. Lists income, expenses, assets, and debts.",
    "12.902(c)": "Long financial affidavit. Use if your income is $50,000 OR MORE/year. More detailed than the short form.",
    "12.902(d)": "Uniform Child Custody Jurisdiction Affidavit — tells the court where your children lived for the past 5 years. Required for any case with kids.",
    "12.902(e)": "Child Support Guidelines Worksheet — calculates child support based on incomes, childcare costs, health insurance, and parenting time.",
    "12.902(f)(1)": "Marital Settlement Agreement for cases with children — write your agreed terms for property, debts, time with kids, and support.",
    "12.902(f)(2)": "Marital Settlement Agreement for cases without children — how you agree to split property and debts.",
    "12.932": "Certificate of Compliance with Mandatory Disclosure — certifies you've shared required financial documents with the other side.",
    "12.990(b)(1)": "Final Judgment of Dissolution with children — the order the judge signs to end your marriage when you have children.",
    "12.990(a)": "Final Judgment of Dissolution without children — the order the judge signs to end your marriage.",
    # Custody
    "12.983(a)": "Petition to Determine Paternity and for Related Relief — for unmarried parents to legally establish fatherhood AND decide custody, time-sharing, and child support.",
    "12.995(a)": "Parenting Plan — your proposed schedule for sharing time with children: which days each parent has them, holidays, vacations, how decisions are made.",
    # Child Support
    "12.905": "Supplemental Petition to Modify Child Support — ask the court to change an existing child support order because your situation changed significantly.",
    # Domestic Violence
    "DV-1": "Petition for Injunction for Protection Against Domestic Violence — ask the court for IMMEDIATE protection. The judge can order the person to stay away from you, your home, and your work.",
    "DV-2": "Petition for Injunction Against Repeat Violence — for repeat violence from someone you don't live with and have no family/dating relationship with.",
    "DV-3": "Petition for Injunction Against Dating Violence — for violence from someone you're dating or have dated.",
    "DV-4": "Petition for Injunction Against Sexual Violence — you don't need a prior relationship with the person.",
    # Name Change
    "12.982(a)": "Petition for Change of Name (Adult) — ask the court to legally change your name. Requires fingerprinting and background check.",
    "12.982(d)": "Final Judgment of Change of Name (Adult) — the order granting your name change. Use this to update your ID, Social Security, and other documents.",
    # Small Claims
    "7.340": "Summons/Notice to Appear for Pretrial Conference — the official notice the court sends to the person you're suing.",
    "7.343": "Fact Information Sheet — after you win, send this to the person who owes you. They must list their assets, bank accounts, employer, and property.",
}


# ── Case Type Definitions ─────────────────────────────────────

@dataclass
class CaseType:
    id: str
    name: str
    description: str
    court: str
    filing_fee: str
    form_numbers: list[str] = field(default_factory=list)
    diy_florida: bool = False
    diy_interview: str = ""
    county_specific: bool = False
    note: str = ""


CASE_TYPES: dict[str, CaseType] = {
    "divorce-with-children": CaseType(
        id="divorce-with-children",
        name="Divorce with Children",
        description="End your marriage when you have minor or dependent children with your spouse.",
        court="Circuit Court (Family Division)",
        filing_fee="$408.00",
        form_numbers=["12.901(b)(1)", "12.902(b)", "12.902(d)", "12.902(e)", "12.995(a)", "12.932"],
    ),
    "divorce-without-children": CaseType(
        id="divorce-without-children",
        name="Divorce without Children",
        description="End your marriage when you have no minor children. Simpler process.",
        court="Circuit Court (Family Division)",
        filing_fee="$408.00",
        form_numbers=["12.901(b)(2)", "12.902(b)"],
        diy_florida=True,
        diy_interview="Simplified Dissolution",
    ),
    "child-custody-timesharing": CaseType(
        id="child-custody-timesharing",
        name="Child Custody / Time-Sharing",
        description="Establish or modify custody and visitation for unmarried parents.",
        court="Circuit Court (Family Division)",
        filing_fee="$300.00",
        form_numbers=["12.983(a)", "12.902(b)", "12.902(d)", "12.902(e)", "12.995(a)"],
    ),
    "child-support-modification": CaseType(
        id="child-support-modification",
        name="Child Support Modification",
        description="Change an existing child support order because your situation changed significantly.",
        court="Circuit Court (Family Division) or DOR Administrative",
        filing_fee="Varies ($0–$300 depending on method)",
        form_numbers=["12.905", "12.902(b)", "12.902(e)"],
    ),
    "domestic-violence-injunction": CaseType(
        id="domestic-violence-injunction",
        name="Domestic Violence Injunction",
        description="Get immediate court protection from someone who has hurt or threatened you.",
        court="Circuit Court",
        filing_fee="$0 (no fee for protection injunctions)",
        diy_florida=True,
        diy_interview="Domestic Violence",
        note="No filing fee. You can go to the courthouse in person and get the forms at the clerk's counter immediately.",
    ),
    "eviction-landlord": CaseType(
        id="eviction-landlord",
        name="Eviction (Landlord)",
        description="Evict a tenant for non-payment of rent or lease violation.",
        court="County Court",
        filing_fee="$185–$300 (varies by county)",
        diy_florida=True,
        diy_interview="Landlord Tenant",
        county_specific=True,
    ),
    "eviction-tenant": CaseType(
        id="eviction-tenant",
        name="Eviction Defense (Tenant)",
        description="Respond to an eviction filing. You have only 5 business days to respond.",
        court="County Court",
        filing_fee="$0 to file answer",
        county_specific=True,
        note="CRITICAL: Only 5 business days to respond. Contact your local legal aid office immediately.",
    ),
    "small-claims": CaseType(
        id="small-claims",
        name="Small Claims",
        description="Sue for money damages up to $8,000. Covers unpaid debts, auto damage, security deposits, unpaid work, and more.",
        court="County Court",
        filing_fee="$55–$300 (varies by amount and county)",
        form_numbers=["7.340", "7.343"],
        diy_florida=True,
        diy_interview="Small Claims",
        county_specific=True,
    ),
    "name-change-adult": CaseType(
        id="name-change-adult",
        name="Adult Name Change",
        description="Legally change your name. Requires fingerprinting and background check before filing.",
        court="Circuit Court",
        filing_fee="$414.00",
        form_numbers=["12.982(a)", "12.982(d)"],
        note="Must complete fingerprinting and background check BEFORE filing. Contact your county clerk for the local name change packet.",
    ),
    "probate-small-estate": CaseType(
        id="probate-small-estate",
        name="Small Estate Probate",
        description="Handle an estate valued under $75,000 after someone dies. Faster and cheaper than formal probate.",
        court="Circuit Court (Probate Division)",
        filing_fee="$232–$345 (varies by county)",
        county_specific=True,
        note="Visit your county clerk's probate division for the county-specific small estate packet. DIY Florida does NOT cover probate.",
    ),
    "probate-full": CaseType(
        id="probate-full",
        name="Full Probate",
        description="Handle a larger estate (over $75,000) after someone dies. Complex process.",
        court="Circuit Court (Probate Division)",
        filing_fee="$400.00",
        county_specific=True,
        note="Formal probate is complex. An attorney is STRONGLY recommended. Visit your county clerk for county-specific forms.",
    ),
    "guardianship": CaseType(
        id="guardianship",
        name="Guardianship",
        description="Become the legal guardian for someone who cannot care for themselves.",
        court="Circuit Court (Probate/Guardianship Division)",
        filing_fee="$400.00",
        county_specific=True,
        note="Requires background check, credit check, and guardianship education. Attorney strongly recommended.",
    ),
    "expungement-sealing": CaseType(
        id="expungement-sealing",
        name="Expungement / Record Sealing",
        description="Seal or expunge a criminal record. Must first get FDLE Certificate of Eligibility.",
        court="Circuit or County Court (where case was filed)",
        filing_fee="$42.00 sealing + $75.00 FDLE fee",
        county_specific=True,
        note="STEP 1: Apply for FDLE Certificate of Eligibility first (2-4 months). You cannot file in court without it.",
    ),
}


# ── Decision Tree ─────────────────────────────────────────────

DecisionNode = dict[str, Any]

DECISION_TREE: dict[str, DecisionNode] = {
    "start": {
        "question": "What is your legal situation about?",
        "options": {
            "family": {"label": "Family or domestic matter (divorce, kids, protection)", "next": "family"},
            "housing": {"label": "Housing (eviction, landlord/tenant dispute)", "next": "housing"},
            "money": {"label": "Someone owes me money", "next": "money"},
            "records": {"label": "Criminal record (expunge/seal)", "result": "expungement-sealing"},
            "estate": {"label": "Estate, will, probate, or guardianship", "next": "estate"},
        },
    },
    "family": {
        "question": "What kind of family matter?",
        "options": {
            "divorce": {"label": "Divorce / ending a marriage", "next": "divorce"},
            "custody": {"label": "Child custody or time-sharing (not married)", "next": "custody"},
            "support": {"label": "Child support — change an existing order", "result": "child-support-modification"},
            "protection": {"label": "Protection from violence / restraining order", "result": "domestic-violence-injunction"},
            "name": {"label": "Change my name", "result": "name-change-adult"},
        },
    },
    "divorce": {
        "question": "Do you have minor or dependent children with your spouse?",
        "options": {
            "yes": {"result": "divorce-with-children"},
            "no": {"result": "divorce-without-children"},
        },
    },
    "custody": {
        "question": "Is paternity (legal fatherhood) already established?",
        "options": {
            "yes": {"label": "Yes — father is on birth certificate or court order exists", "result": "child-custody-timesharing"},
            "no": {"label": "No — need to establish paternity first", "result": "child-custody-timesharing"},
        },
    },
    "housing": {
        "question": "Are you the landlord or the tenant?",
        "options": {
            "landlord": {"label": "I'm the landlord — need to evict a tenant", "result": "eviction-landlord"},
            "tenant": {"label": "I'm the tenant — being evicted or have a dispute", "result": "eviction-tenant"},
        },
    },
    "money": {
        "question": "What kind of debt or money claim?",
        "options": {
            "auto": {"label": "Car accident damage", "result": "small-claims"},
            "goods": {"label": "Someone bought goods and didn't pay", "result": "small-claims"},
            "work": {"label": "I did work or provided materials and wasn't paid", "result": "small-claims"},
            "loan": {"label": "I lent money and they won't pay back", "result": "small-claims"},
            "deposit": {"label": "Landlord kept my security deposit", "result": "small-claims"},
            "other": {"label": "Other — less than $8,000", "result": "small-claims"},
        },
    },
    "estate": {
        "question": "What do you need?",
        "options": {
            "probate_small": {"label": "Handle a small estate (under $75,000) after someone died", "result": "probate-small-estate"},
            "probate_full": {"label": "Handle a larger estate (over $75,000) after someone died", "result": "probate-full"},
            "guardianship": {"label": "Become guardian for someone who can't care for themselves", "result": "guardianship"},
        },
    },
}


# ── Public API ────────────────────────────────────────────────

def get_case_type(case_id: str) -> CaseType | None:
    """Get case type info by ID."""
    return CASE_TYPES.get(case_id)


def list_case_types() -> list[CaseType]:
    """Return all case types."""
    return list(CASE_TYPES.values())


def get_decision_tree_node(node_id: str) -> DecisionNode | None:
    """Get a decision tree node by ID."""
    return DECISION_TREE.get(node_id)


def get_form_explanation(form_number: str) -> str:
    """Get a plain-English explanation for a form number."""
    return FORM_EXPLANATIONS.get(form_number, "")


def get_tree_root() -> DecisionNode:
    """Get the root of the decision tree."""
    return DECISION_TREE["start"]
