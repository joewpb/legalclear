"""I-2d — anonymous resumable claim codes.

POST /api/claims        — issue a claim code bound to a session.
GET  /api/claims/{code} — resume a claim: state + the session's claim_facts
                           regime. Unknown and wrong-but-well-formed codes
                           both 404 with the identical body — no existence
                           oracle.

The code is a CREDENTIAL: unguessable (128-bit urlsafe random, never
sequential), stored only as sha256(code). See src/core/claim_codes.py.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.core.claim_codes import hash_code, issue_claim_code
from src.core.claim_regime import resolve_regime
from src.api.limiter import limiter
from src.memory.db import DBWriteError, DatabaseManager

router = APIRouter(prefix="/api/claims")
_db = DatabaseManager()

_UNKNOWN_CODE_DETAIL = "No claim found for this code."


class CreateClaimRequest(BaseModel):
    session_id: str | None = None


@router.post("")
@limiter.limit("10/minute")
async def create_claim(request: Request, body: CreateClaimRequest):
    code, code_hash = issue_claim_code()
    try:
        claim_id = _db.create_claim(code_hash, body.session_id)
    except DBWriteError as e:
        raise HTTPException(status_code=503, detail="Could not create a claim code.") from e
    return {"code": code, "phase": "fire.p0.immediate"}


@router.get("/{code}")
@limiter.limit("10/minute")
async def get_claim(request: Request, code: str):
    claim = _db.get_claim_by_code_hash(hash_code(code))
    if claim is None:
        raise HTTPException(status_code=404, detail=_UNKNOWN_CODE_DETAIL)

    _db.touch_claim(claim["id"])

    fact = _db.get_claim_fact(claim["session_id"]) if claim.get("session_id") else None
    inception = fact.get("policy_inception_date") if fact else None
    regime = resolve_regime(date.fromisoformat(inception) if inception else None)

    return {
        "phase": claim["phase"],
        "phase_entered_at": claim["phase_entered_at"],
        "created_at": claim["created_at"],
        "last_seen_at": claim["last_seen_at"],
        "claim_regime": {"regime": regime},
    }
