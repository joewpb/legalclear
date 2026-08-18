"""Phase 4 — Deadline Engine HTTP endpoints."""

import logging
import re

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import require_api_key
from src.core.upl import apply_disclaimer
from src.memory.db import DatabaseManager
from deadline.rules import RULES, SERVICE_POSTED

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/deadline", tags=["deadline"])
db = DatabaseManager()

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SERVICE_METHODS = ("personal", "substitute", "posted", "mail", "eservice", "unknown")


class ServiceDateRequest(BaseModel):
    """B5-c1 — user-supplied service date, validation only (no recompute)."""

    service_method: str = Field(pattern="^(" + "|".join(_SERVICE_METHODS) + ")$")
    service_date: str
    clerk_mailing_date: Optional[str] = None
    trigger_event_id: Optional[str] = None


_MIN_SERVICE_DATE = date(2000, 1, 1)


def _parse_iso_date(value: str, field_name: str) -> str:
    if not _DATE_RE.match(value):
        raise HTTPException(status_code=422, detail=f"{field_name} must be in YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{field_name} is not a valid calendar date") from e
    return value, parsed


def _parse_and_check_range(value: str, field_name: str) -> str:
    value, parsed = _parse_iso_date(value, field_name)
    max_date = date.today() + timedelta(days=7)
    if parsed < _MIN_SERVICE_DATE or parsed > max_date:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} must be between {_MIN_SERVICE_DATE.isoformat()} and {max_date.isoformat()}",
        )
    return value
# Decision 2 — "I don't know" escalates rather than guessing a service method;
# it also tells the user where to find the real answer instead of just saying no.
GUIDANCE_UNKNOWN_SERVICE_METHOD = (
    "Service method could not be determined, so no deadline was computed. "
    "The return of service is filed with the clerk of court, and the case "
    "docket shows the date service was made — check the docket or the "
    "clerk's file for the exact service date and method, then supply it."
)

# Decision 6 — posted service runs from later-of(posting, mailing); without
# the mailing date there is nothing to compute the later-of from.
GUIDANCE_POSTED_WITHOUT_MAILING_DATE = (
    "This document was served by posting. The deadline for posted service "
    "runs from the later of the posting date or the mailing date shown on "
    "the return of service, and that mailing date is not yet on file. The "
    "return of service is filed with the clerk of court, and the case "
    "docket shows the mailing date — check the docket or the clerk's file, "
    "then supply the mailing date."
)

_DEADLINE_SELECT_COLUMNS = (
    "id,label,due_date,governing_rule,consequence_if_missed,"
    "severity,confidence,escalation_recommended,"
    "computation_trace,reminder_state,created_at"
)

# G1-1 — governing_rule -> required_anchors, so a deadline row can be checked
# against document_service_facts without needing the rule_key (deadlines rows
# only carry governing_rule, not the RULES dict key that produced them).
_REQUIRED_ANCHORS_BY_GOVERNING_RULE = {
    rule["governing_rule"]: rule.get("required_anchors")
    for rule in RULES.values()
}


def _anchor_for_deadline(
    governing_rule: str,
    computation_trace: list,
    service_fact: dict | None,
) -> tuple[str | None, str, str | None]:
    """Derive (anchor_date, anchor_provenance, anchor_note) for one deadline row.

    computation_trace[0] is always the "Trigger event date" step written by
    deadline/compute.py's `_compute_single` (for posted service, this is
    already the later-of-posting-and-mailing effective date) — so the anchor
    date itself never needs re-deriving here, only its provenance.

    Provenance: this rule's required_anchors says whether a "served" anchor
    was even in play for this deadline; document_service_facts (B5-f3) is the
    single source of truth for whether that anchor was user-supplied. Rules
    anchored on something else (date_of_loss, rendered, etc.) are always
    "extracted" — a user-supplied service date never feeds those.
    """
    anchor_date = computation_trace[0].get("date") if computation_trace else None

    required_anchors = _REQUIRED_ANCHORS_BY_GOVERNING_RULE.get(governing_rule)
    served_anchor = bool(required_anchors) and "served" in required_anchors
    user_service_date = service_fact.get("service_date") if service_fact else None

    if not (served_anchor and user_service_date):
        return anchor_date, "extracted", None

    anchor_note = None
    service_method = (service_fact.get("service_method") or "").strip().lower()
    clerk_mailing_date = service_fact.get("clerk_mailing_date")
    if service_method == SERVICE_POSTED and clerk_mailing_date and clerk_mailing_date != user_service_date:
        anchor_note = (
            "Anchor is the later of the user-supplied posting date "
            f"({user_service_date}) and the clerk's certificate-of-mailing "
            f"date ({clerk_mailing_date}), extracted from the docket."
        )
    return anchor_date, "user_supplied", anchor_note


def _escalation_response(guidance: str) -> dict:
    """Shape for the I-don't-know contract: no pipeline run, no deadline write."""
    return {
        "recompute": "escalated",
        "escalation_needed": True,
        "escalation_reasons": [guidance],
        "guidance": guidance,
        "deadlines": [],
    }


async def _recompute_deadlines(
    document_id: str,
    service_method: str | None,
    clerk_mailing_date: str | None = None,
) -> dict:
    """Recompute deadlines for a document after a service-date supply/edit.

    Seam for B5-c1: the PUT /api/deadline/{document_id}/service-date endpoint
    persists user_service_date/user_service_method itself, then calls this
    helper with the same service_method (and, once B5-b lands, the posted
    document's clerk_mailing_date) to get the refreshed deadlines or the
    escalation payload. Edit uses this same path as initial supply — there is
    no separate branch, since the endpoint upserts the trigger_events columns
    before either call.

    Decision 2: an unknown service method escalates instead of computing.
    Decision 6: posted service without a mailing date escalates instead of
    computing. In both cases no deadline row is written or refreshed.
    """
    method = (service_method or "").strip().lower()

    if not method or method == "unknown":
        return _escalation_response(GUIDANCE_UNKNOWN_SERVICE_METHOD)

    if method == SERVICE_POSTED and not clerk_mailing_date:
        return _escalation_response(GUIDANCE_POSTED_WITHOUT_MAILING_DATE)

    from deadline.pipeline import run_deadline_pipeline

    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    text = doc.get("document_text") or ""
    pipeline_result = await run_deadline_pipeline(document_id, text, db)

    deadlines: list = []
    try:
        rows = (db.client.table("deadlines")
                .select(_DEADLINE_SELECT_COLUMNS)
                .eq("document_id", document_id)
                .order("due_date")
                .execute())
        deadlines = rows.data or []
    except Exception as e:
        logger.error("Failed to fetch recomputed deadlines: %s", e)

    return {
        "recompute": "complete",
        "deadlines": deadlines,
        "escalation_needed": pipeline_result.get("escalation_needed", False),
        "escalation_reasons": pipeline_result.get("escalation_reasons", []),
    }


@router.post("/analyze/{document_id}", dependencies=[Depends(require_api_key)])
async def analyze_document(document_id: str):
    """Run the deadline pipeline on an already-ingested document.

    Fetches document_text from the DB, runs Stage 1 (LLM extraction) and
    Stage 2 (deterministic computation), writes trigger_events and deadlines.
    """
    from deadline.pipeline import run_deadline_pipeline

    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    doc = db.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    text = doc.get("document_text") or ""
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Document has no extractable text. Upload the document first."
        )

    result = await run_deadline_pipeline(document_id, text, db)
    return apply_disclaimer(result, lang="en")


@router.get("/{document_id}/deadlines")
async def get_deadlines(document_id: str, session_id: Optional[str] = None):
    """Return all computed deadlines for a document, ordered by due_date."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = db.get_document(document_id)
    if not doc or not session_id or doc.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = (db.client.table("deadlines")
                  .select(_DEADLINE_SELECT_COLUMNS)
                  .eq("document_id", document_id)
                  .order("due_date")
                  .execute())
        rows = result.data or []
        service_fact = db.get_document_service_fact(document_id)
        for row in rows:
            anchor_date, anchor_provenance, anchor_note = _anchor_for_deadline(
                row.get("governing_rule", ""),
                row.get("computation_trace") or [],
                service_fact,
            )
            row["anchor_date"] = anchor_date
            row["anchor_provenance"] = anchor_provenance
            row["anchor_note"] = anchor_note
        return apply_disclaimer({"deadlines": rows}, lang="en")
    except Exception as e:
        logger.error("get_deadlines failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve deadlines") from e


@router.get("/{document_id}/trigger-events")
async def get_trigger_events(document_id: str, session_id: Optional[str] = None):
    """Return extracted trigger events for a document."""
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = db.get_document(document_id)
    if not doc or not session_id or doc.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = (db.client.table("trigger_events")
                  .select("*")
                  .eq("document_id", document_id)
                  .order("created_at")
                  .execute())
        return apply_disclaimer({"trigger_events": result.data or []}, lang="en")
    except Exception as e:
        logger.error("get_trigger_events failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not retrieve trigger events") from e


@router.put("/{document_id}/service-date", dependencies=[Depends(require_api_key)])
async def set_service_date(document_id: str, body: ServiceDateRequest, session_id: Optional[str] = None):
    """Record a user-supplied service date for a document's trigger event.

    B5-c1 scope: endpoint + validation only. No recompute, no deadline
    writes, no escalation contract (that is B5-c2's job). Every write from
    this endpoint sets service_date_provenance='user_supplied' — there is
    no code path here that writes 'extracted'.

    Decision 6: posted service requires both the posting date (service_date)
    and the date the clerk mailed the papers (clerk_mailing_date), so a
    missing mailing date is a 422 rather than a silent fallback.

    B5-f3: this write goes to document_service_facts (one row per document),
    never to trigger_events — trigger_events rows are pipeline-owned and get
    rewritten on every recompute, which used to clobber user-supplied values
    stored there. The pipeline reads document_service_facts back as a unit
    on every recompute (deadline/pipeline.py) so clerk_mailing_date keeps
    feeding compute_deadline_for_event on later recompute/re-extraction
    passes, not just this request's.

    Response contract: after the upsert this endpoint calls
    `_recompute_deadlines` (B5-c2 seam) — `recompute` is "complete" with
    refreshed deadlines, or "escalated" per Decision 2/6 with zero deadline
    writes.
    """
    if db.client is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doc = db.get_document(document_id)
    if not doc or not session_id or doc.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail="Document not found")

    service_date = _parse_and_check_range(body.service_date, "service_date")

    clerk_mailing_date = None
    if body.service_method == "posted":
        if not body.clerk_mailing_date:
            raise HTTPException(
                status_code=422,
                detail="clerk_mailing_date is required when service_method is 'posted' "
                       "(Decision 6): a mailing date unavailable must escalate, never "
                       "compute from the posting date alone.",
            )
        clerk_mailing_date, _ = _parse_iso_date(body.clerk_mailing_date, "clerk_mailing_date")
    elif body.clerk_mailing_date:
        clerk_mailing_date, _ = _parse_iso_date(body.clerk_mailing_date, "clerk_mailing_date")

    try:
        te_query = db.client.table("trigger_events").select("id").eq("document_id", document_id)
        if body.trigger_event_id:
            te_query = te_query.eq("id", body.trigger_event_id)
        te_result = te_query.order("created_at").execute()
        rows = te_result.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="No trigger event found for this document")
        trigger_event_id = rows[0]["id"]

        update_payload = {
            "user_service_date": service_date,
            "user_service_method": body.service_method,
            "service_date_provenance": "user_supplied",
        }
        if clerk_mailing_date:
            update_payload["clerk_mailing_date"] = clerk_mailing_date

        ok = db.upsert_document_service_fact(
            document_id,
            service_date=service_date,
            service_method=body.service_method,
            clerk_mailing_date=clerk_mailing_date,
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Could not save service date")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("set_service_date failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not save service date") from e

    recomputed = await _recompute_deadlines(
        document_id, body.service_method, clerk_mailing_date
    )
    response = {
        "document_id": document_id,
        "trigger_event_id": trigger_event_id,
        **update_payload,
        **recomputed,
    }
    if clerk_mailing_date:
        response["clerk_mailing_date"] = clerk_mailing_date
    return apply_disclaimer(response, lang="en")
