"""Phase 3 — Statutes, Court Rules & Local Administrative Orders corpus.

All endpoints are read-only lookups against verbatim official text.
No LLM involvement here — plain-language explanations live in the
explanation agents, not in this router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.memory.db import DatabaseManager
from src.core.upl import apply_disclaimer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/law", tags=["law"])
db = DatabaseManager()


# ── Statutes ──────────────────────────────────────────────────────────────────

@router.get("/statutes")
async def lookup_statute(citation: Optional[str] = None,
                         chapter: Optional[str] = None,
                         section: Optional[str] = None):
    """Exact-citation or chapter/section lookup against Florida Statutes.

    Examples:
      GET /api/law/statutes?citation=Fla.+Stat.+%C2%A7+83.60(2)
      GET /api/law/statutes?chapter=83&section=83.60
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not citation and not (chapter and section):
        raise HTTPException(
            status_code=400,
            detail="Provide either citation= or both chapter= and section="
        )
    try:
        q = db.client.table("statutes").select(
            "citation,chapter,section,subsection,title,text,"
            "effective_date,source_url"
        )
        if citation:
            q = q.eq("citation", citation)
        else:
            q = q.eq("chapter", chapter).eq("section", section)
        result = q.execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Statute not found")
        return apply_disclaimer({"statutes": result.data}, lang="en")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("statute lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Lookup failed")


# ── Court Rules ───────────────────────────────────────────────────────────────

@router.get("/rules")
async def lookup_rule(citation: Optional[str] = None,
                      rule_set: Optional[str] = None,
                      rule_number: Optional[str] = None):
    """Exact-citation or rule_set/rule_number lookup against FL court rules.

    Examples:
      GET /api/law/rules?citation=Fla.+R.+Civ.+P.+1.140(a)
      GET /api/law/rules?rule_set=civil_procedure&rule_number=1.140
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not citation and not (rule_set and rule_number):
        raise HTTPException(
            status_code=400,
            detail="Provide either citation= or both rule_set= and rule_number="
        )
    try:
        q = db.client.table("court_rules").select(
            "citation,rule_set,rule_number,subsection,title,text,"
            "effective_date,source_url"
        )
        if citation:
            q = q.eq("citation", citation)
        else:
            q = q.eq("rule_set", rule_set).eq("rule_number", rule_number)
        result = q.execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Rule not found")
        return apply_disclaimer({"rules": result.data}, lang="en")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("rule lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Lookup failed")


# ── Local Administrative Orders ───────────────────────────────────────────────

@router.get("/administrative-orders")
async def list_administrative_orders(circuit: Optional[int] = None):
    """List local administrative orders, optionally filtered by circuit."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        q = db.client.table("local_administrative_orders").select(
            "circuit,ao_number,subject,effective_date,expiration_date,summary,source_url"
        ).order("circuit").order("ao_number")
        if circuit is not None:
            q = q.eq("circuit", circuit)
        result = q.execute()
        return apply_disclaimer({"administrative_orders": result.data or []}, lang="en")
    except Exception as e:
        logger.error("AO lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Lookup failed")


# ── Court Closures ────────────────────────────────────────────────────────────

@router.get("/closures")
async def list_closures(circuit: Optional[int] = None,
                        date: Optional[str] = None):
    """List court closures for deadline-engine use.

    Pass circuit=0 for statewide closures.
    Pass date= (YYYY-MM-DD) to check a specific date.
    The deadline engine should query both circuit=0 AND the specific circuit.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        q = db.client.table("court_closures").select(
            "circuit,county,closure_date,reason,source"
        ).order("closure_date")
        if circuit is not None:
            q = q.eq("circuit", circuit)
        if date:
            q = q.eq("closure_date", date)
        result = q.execute()
        return {"closures": result.data or []}
    except Exception as e:
        logger.error("closures lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Lookup failed")
