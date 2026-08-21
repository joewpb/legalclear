"""Module 5 — Property & Casualty router.

POST /api/property-casualty/explain — streaming SSE.
Accepts entities + optional document upload.

POST /api/property-casualty/facts — I-2c capture endpoint. Deterministic,
no LLM. The ONLY writer of public.claim_facts (see
backend/tests/test_claim_facts.py for mechanical enforcement).
"""

import json
from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.property_casualty import PropertyCasualtyExplainer
from src.api.limiter import limiter
from src.core.claim_regime import resolve_regime
from src.memory.db import DatabaseManager

router = APIRouter(prefix="/api/property-casualty")
_explainer = PropertyCasualtyExplainer()
_db = DatabaseManager()


class ClaimFactsRequest(BaseModel):
    """I-2c — the user is asked; this is never extracted or inferred.

    Keyed by session_id (Option A ruling 2026-08-20): the P&C explain flow
    creates or reuses a session, and claim_facts hangs off that session.
    """

    session_id: str
    policy_inception_date: date | None = None


@router.post("/facts")
async def capture_claim_facts(body: ClaimFactsRequest):
    """Upsert the user-supplied policy inception date for a session.

    Always writes provenance='user_supplied'. Unknown (``None``) is stored
    as-is — it is not defaulted to a regime, it escalates when the explain
    flow reads it back (see PropertyCasualtyExplainer._resolve_claim_regime).
    """
    ok = _db.upsert_claim_fact(
        body.session_id,
        body.policy_inception_date.isoformat() if body.policy_inception_date else None,
    )
    if not ok:
        raise HTTPException(status_code=503, detail="Could not save policy inception date.")
    return {
        "session_id": body.session_id,
        "policy_inception_date": body.policy_inception_date,
        "provenance": "user_supplied",
        "regime": resolve_regime(body.policy_inception_date),
    }


@router.post("/explain")
@limiter.limit("10/minute")
async def explain_property_casualty(
    request: Request,
    sub_type: str = Form(default="unknown"),
    entities_json: str = Form(default="{}"),
    language: str = Form(default="en"),
    file: UploadFile | None = File(default=None),
    session_id: str | None = Form(default=None),
    user_id: str = Form(default="anon"),
):
    """Explain a Florida property/casualty situation with optional document.

    I-2c / Option A (2026-08-20): every explain call runs under a session —
    the caller's existing session_id is reused, or a new one is created here
    and returned in the response so the frontend can reuse it for /facts
    capture and subsequent explain calls.
    """

    # Parse entities from JSON string
    try:
        entities: dict = json.loads(entities_json)
    except (json.JSONDecodeError, TypeError):
        entities = {}

    # Read optional file
    file_bytes: bytes | None = None
    filename: str | None = None
    if file is not None:
        file_bytes = await file.read()
        filename = file.filename

    if not session_id:
        session_id = _db.create_session(
            user_id=user_id,
            filename=filename or "property-casualty-session",
            token_count=0,
            price_tier="free",
            price_usd=0.0,
            payment_type="free",
        )

    async def _stream():
        async for chunk in _explainer.explain_stream(
            sub_type=sub_type if sub_type in ("first_party_property", "insurance_bad_faith", "premises_liability", "unknown") else "unknown",
            entities=entities,
            language=language if language in ("en", "es") else "en",
            file_bytes=file_bytes,
            filename=filename,
            session_id=session_id,
        ):
            yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
