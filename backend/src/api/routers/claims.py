"""I-2d + I-4 — anonymous resumable claim codes and the claim state machine
API (Phase I finale, 2026-08-23).

POST /api/claims                      — issue a claim code bound to a session;
                                        optional peril / date_of_loss / sub_type.
                                        A date_of_loss automatically records the
                                        claim's opening date_of_loss event.
POST /api/claims/{code}/events        — record a trigger/red-flag event. The
                                        trigger name must be in the deterministic
                                        vocabulary (content-layer phase triggers
                                        + red-flag names); anything else is 422.
POST /api/claims/{code}/details       — replace the user-supplied details
                                        object (artifact generation reads it).
GET  /api/claims/{code}               — full state snapshot: phase machine,
                                        red flags, escalation, regime.
GET  /api/claims/{code}/guide         — the I-5 payload: active/upcoming phase
                                        content, computed deadlines, flags,
                                        persistent disclaimer.

Unknown and wrong-but-well-formed codes both 404 with the identical body —
no existence oracle. The code is a CREDENTIAL: unguessable (128-bit urlsafe
random, never sequential), stored only as sha256(code). See
src/core/claim_codes.py.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.agents.artifacts import ARTIFACT_CATALOG, build_artifact, missing_fields
from src.agents.claim_state import compute_state, trigger_vocabulary
from src.agents.property_casualty import PropertyCasualtyExplainer
from src.agents.red_flags import (
    USER_DECLARED_FLAGS,
    USER_DECLARED_FLAG_NAMES,
    active_flags,
    escalation,
)
from src.api.limiter import limiter
from src.content.loader import load_active_content
from src.core.claim_codes import hash_code, issue_claim_code
from src.core.claim_regime import resolve_regime
from src.core.upl import apply_disclaimer
from src.memory.db import DBWriteError, DatabaseManager

router = APIRouter(prefix="/api/claims")
_db = DatabaseManager()
_explainer = PropertyCasualtyExplainer()

_UNKNOWN_CODE_DETAIL = "No claim found for this code."

_PERILS = ("fire", "smoke", "water", "wind", "hurricane", "flood", "theft", "sinkhole", "tree_fall", "mold", "condo", "vandalism")
_SUB_TYPES = ("first_party_property", "insurance_bad_faith", "premises_liability", "unknown")


def _records():
    return load_active_content()


def _vocabulary() -> set[str]:
    return trigger_vocabulary(_records()) | set(USER_DECLARED_FLAG_NAMES)


def _require_claim(code: str) -> dict:
    claim = _db.get_claim_by_code_hash(hash_code(code))
    if claim is None:
        raise HTTPException(status_code=404, detail=_UNKNOWN_CODE_DETAIL)
    return claim


def _parse_loss_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


class CreateClaimRequest(BaseModel):
    session_id: str | None = None
    peril: str = "fire"
    date_of_loss: str | None = None
    sub_type: str = "first_party_property"


class AddEventRequest(BaseModel):
    trigger_name: str
    occurred_at: str | None = None
    note: str | None = Field(default=None, max_length=500)


class UpdateDetailsRequest(BaseModel):
    details: dict = Field(default_factory=dict)


@router.post("")
@limiter.limit("10/minute")
async def create_claim(request: Request, body: CreateClaimRequest):
    peril = body.peril if body.peril in _PERILS else "fire"
    sub_type = body.sub_type if body.sub_type in _SUB_TYPES else "first_party_property"
    loss_date = _parse_loss_date(body.date_of_loss)

    code, code_hash = issue_claim_code()
    if not body.session_id:
        # I-9 (2026-08-23): a claim must be able to carry claim_facts
        # (policy inception date -> regime), and claim_facts is keyed by
        # session. Anonymous claims therefore get their own session at
        # creation — the same pattern as the explain flow. user_id NULL
        # (never a non-UUID placeholder).
        try:
            session_id = _db.create_session(
                user_id=None,
                filename="claim-guide",
                token_count=0,
                price_tier="free",
                price_usd=0.0,
                payment_type="free",
            )
        except DBWriteError as e:
            raise HTTPException(status_code=503, detail="Could not create a session for this claim.") from e
    else:
        session_id = body.session_id

    try:
        claim_id = _db.create_claim(code_hash, session_id)
    except DBWriteError as e:
        raise HTTPException(status_code=503, detail="Could not create a claim code.") from e

    # The opening event is claim data, not a user-reported trigger — record
    # it so the log is complete from t0 (p0's entry_trigger is date_of_loss).
    if loss_date is not None:
        try:
            _db.add_claim_event(claim_id, "date_of_loss", occurred_at=loss_date.isoformat(), source="claim")
        except DBWriteError as e:
            raise HTTPException(status_code=503, detail="Claim created but its opening event could not be recorded.") from e

    return {
        "code": code,
        "phase": "fire.p0.immediate",
        "peril": peril,
        "date_of_loss": loss_date.isoformat() if loss_date else None,
        "session_id": session_id,
    }


@router.post("/{code}/events")
@limiter.limit("10/minute")
async def add_claim_event(request: Request, code: str, body: AddEventRequest):
    claim = _require_claim(code)
    vocab = _vocabulary()
    if body.trigger_name not in vocab:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown trigger name {body.trigger_name!r}. Valid names: {sorted(vocab)}",
        )
    try:
        event = _db.add_claim_event(
            claim["id"], body.trigger_name,
            occurred_at=body.occurred_at,
            note=body.note,
        )
    except DBWriteError as e:
        raise HTTPException(status_code=503, detail="Could not record the event.") from e
    return {"recorded": event["trigger_name"], "occurred_at": event["occurred_at"]}


@router.post("/{code}/details")
@limiter.limit("10/minute")
async def update_claim_details(request: Request, code: str, body: UpdateDetailsRequest):
    claim = _require_claim(code)
    try:
        _db.update_claim_details(claim["id"], body.details)
    except DBWriteError as e:
        raise HTTPException(status_code=503, detail="Could not save claim details.") from e
    return {"saved": True}


def _claim_snapshot(claim: dict, lang: str = "en") -> dict:
    """Full deterministic snapshot for a claim row. No LLM anywhere."""
    events = _db.get_claim_events(claim["id"])
    records = _records()

    state = compute_state(claim, events, records)
    flags = active_flags(events)
    esc = escalation(flags)

    fact = _db.get_claim_fact(claim["session_id"]) if claim.get("session_id") else None
    inception = fact.get("policy_inception_date") if fact else None
    regime = resolve_regime(date.fromisoformat(inception) if inception else None)

    snapshot: dict = {
        "phase": claim["phase"],
        "created_at": claim["created_at"],
        "last_seen_at": claim["last_seen_at"],
        "state": state,
        "claim_regime": {"regime": regime},
        "red_flags": flags,
        "escalation": esc,
        "details": claim.get("details") or {},
    }
    return apply_disclaimer(snapshot, lang=lang)


@router.get("/{code}/artifacts")
@limiter.limit("10/minute")
async def list_artifacts(request: Request, code: str):
    """Artifact catalog for this claim, with per-artifact availability and
    the detail fields still needed before generation is useful."""
    claim = _require_claim(code)
    _db.touch_claim(claim["id"])
    details = dict(claim.get("details") or {})
    if claim.get("date_of_loss"):
        details["date_of_loss"] = claim["date_of_loss"]
    missing = missing_fields(details)
    return apply_disclaimer({
        "artifacts": ARTIFACT_CATALOG,
        "missing_fields": missing,
    }, lang="en")


@router.get("/{code}/artifacts/{artifact_id}")
@limiter.limit("10/minute")
async def download_artifact(request: Request, code: str, artifact_id: str):
    """Download one generated artifact. Deterministic — no LLM, no dates
    computed here beyond what the deadline engine already produced."""
    if artifact_id not in ARTIFACT_CATALOG:
        raise HTTPException(status_code=404, detail="Unknown artifact.")
    claim = _require_claim(code)
    _db.touch_claim(claim["id"])

    events = _db.get_claim_events(claim["id"])

    loss_raw = claim.get("date_of_loss")
    loss_date = _parse_loss_date(loss_raw) if isinstance(loss_raw, str) else (
        loss_raw if isinstance(loss_raw, date) else None
    )
    fact = _db.get_claim_fact(claim["session_id"]) if claim.get("session_id") else None
    inception = fact.get("policy_inception_date") if fact else None
    regime = resolve_regime(date.fromisoformat(inception) if inception else None)
    deadlines: list[dict] = []
    if loss_date is not None and regime != "unknown":
        deadlines = _explainer._compute_deadlines(loss_date, regime=regime)

    details = dict(claim.get("details") or {})
    if claim.get("date_of_loss"):
        details["date_of_loss"] = claim["date_of_loss"]

    payload, mime, filename = build_artifact(artifact_id, claim, events, deadlines, details)
    return Response(
        content=payload,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{code}")
@limiter.limit("10/minute")
async def get_claim(request: Request, code: str):
    claim = _require_claim(code)
    _db.touch_claim(claim["id"])
    return _claim_snapshot(claim)


@router.get("/{code}/guide")
@limiter.limit("10/minute")
async def get_claim_guide(request: Request, code: str):
    """I-5 payload — the Claim Guide screen's data contract.

    Deterministic end to end: content records for the claim's peril (all
    phases, status-tagged), computed deadlines via the existing deadline
    engine (zero date math here), red flags, escalation, and the persistent
    disclaimer.
    """
    claim = _require_claim(code)
    _db.touch_claim(claim["id"])
    events = _db.get_claim_events(claim["id"])
    records = _records()
    state = compute_state(claim, events, records)
    flags = active_flags(events)
    esc = escalation(flags)

    peril = claim.get("peril") or "fire"
    phase_payloads: list[dict] = []
    for record in sorted(records, key=lambda r: r.sequence):
        if peril not in record.peril:
            continue
        st = next((p for p in state["phases"] if p["phase_id"] == record.phase_id), None)
        phase_payloads.append({
            "phase_id": record.phase_id,
            "sequence": record.sequence,
            "status": st["status"] if st else "upcoming",
            "extended": st["extended"] if st else False,
            "title": record.title,
            "plain_summary": record.plain_summary,
            "do_now": [d.model_dump() for d in record.do_now],
            "never_do": [d.model_dump() for d in record.never_do],
            "watch_for": [w.model_dump() for w in record.watch_for],
            "documents": record.documents,
            "authority": record.authority,
            "effective_date": record.effective_date.isoformat(),
        })

    # ── computed deadlines (engine; skip-and-escalate anchors built in) ──
    deadlines: list[dict] = []
    loss_raw = claim.get("date_of_loss")
    loss_date = _parse_loss_date(loss_raw) if isinstance(loss_raw, str) else (
        loss_raw if isinstance(loss_raw, date) else None
    )
    fact = _db.get_claim_fact(claim["session_id"]) if claim.get("session_id") else None
    inception = fact.get("policy_inception_date") if fact else None
    regime = resolve_regime(date.fromisoformat(inception) if inception else None)
    if loss_date is not None and regime != "unknown":
        deadlines = _explainer._compute_deadlines(loss_date, regime=regime)

    today = datetime.now(timezone.utc).date()
    due_this_week: list[dict] = []
    for dl in deadlines:
        if dl.get("is_past"):
            continue
        try:
            due = date.fromisoformat(dl["due_date"])
        except (ValueError, TypeError):
            continue
        if today <= due <= today + timedelta(days=7):
            due_this_week.append(dl)

    guide: dict = {
        "peril": peril,
        "state": state,
        "phases": phase_payloads,
        "deadlines": deadlines,
        "due_this_week": due_this_week,
        "claim_regime": {"regime": regime},
        "red_flags": flags,
        "red_flag_catalog": USER_DECLARED_FLAGS,
        "escalation": esc,
        "details": claim.get("details") or {},
    }
    return apply_disclaimer(guide, lang="en")
