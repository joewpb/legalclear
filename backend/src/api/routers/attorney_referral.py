"""Attorney referral intake — AI-guided chat + user profile + submission.

Flow:
  POST /intake     → continue an AI-guided conversation (stateless — client
                     sends the full conversation so far; backend appends the
                     next AI response).
  POST /submit     → finalize the intake, save to DB, mark for attorney review.
  POST /users      → create or update a user profile.
  GET  /users/{id} → fetch a user profile by ID.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...core.config import settings
from ...memory.db import DatabaseManager
from ..dependencies import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attorney-referral", tags=["attorney-referral"])
db = DatabaseManager()

# Keys from settings (central config — not raw os.environ)
_ANTHROPIC_KEY = settings.ANTHROPIC_API_KEY
_DEEPSEEK_KEY = settings.DEEPSEEK_API_KEY


# ── Models ─────────────────────────────────────────────────────────────────────

class IntakeRequest(BaseModel):
    conversation: list[dict[str, str]] = Field(default_factory=list)
    user_id: str | None = None


class IntakeResponse(BaseModel):
    role: str = "assistant"
    content: str
    stage: str
    user_id: str | None = None


class UserProfileRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    case_category: str | None = None
    case_summary: str | None = None
    urgency: str = "standard"


class SubmitRequest(BaseModel):
    user_id: str
    conversation: list[dict[str, str]]
    intake_summary: str


# ── System prompt ───────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an attorney intake assistant for LegalClear, a Florida
legal-information platform. Gather information an attorney needs to evaluate a case.

Stages (follow in order):
1. GREETING — brief intro, ask name
2. CASE_TYPE — ask what kind of legal issue (eviction, injury, family, criminal, contract, employment)
3. DETAILS — 2-3 questions: what happened, when, where in FL, who involved, desired outcome
4. CONTACT — ask email + phone. If declined: "That's okay, but it helps us match you faster."
5. SUMMARY — summarize what was gathered, ask if anything missing
6. DONE — confirm submission, set expectations (1-2 business days)

Rules:
- Warm, patient, non-judgmental. 2-3 sentences max per response.
- NEVER give legal advice. Say "I'll make sure the attorney knows you asked."
- Urgent (court <72h, eviction, arrest) → tag URGENT, tell them to call 800-342-8011.
- Sensitive info (SSN, bank) → "The attorney will ask if relevant."
- Return ONLY: stage name on first line, then your response."""


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.post("/users", dependencies=[Depends(require_api_key)])
def upsert_user(req: UserProfileRequest) -> dict[str, Any]:
    """Create or update a user profile. Returns the user_id."""
    now = datetime.now(UTC).isoformat()

    # Try to find existing user by email
    user_id = None
    if req.email and db.client:
        existing = (
            db.client.table("user_profiles")
            .select("id")
            .eq("email", req.email)
            .limit(1)
            .execute()
        )
        if existing.data:
            user_id = existing.data[0]["id"]

    payload = {
        "email": req.email,
        "full_name": req.full_name,
        "phone": req.phone,
        "case_category": req.case_category,
        "case_summary": req.case_summary,
        "urgency": req.urgency,
        "updated_at": now,
    }

    if user_id and db.client:
        db.client.table("user_profiles").update(payload).eq("id", user_id).execute()
    elif db.client:
        payload["id"] = str(uuid.uuid4())
        payload["created_at"] = now
        r = db.client.table("user_profiles").insert(payload).execute()
        if r.data:
            user_id = r.data[0]["id"]

    return {"user_id": user_id, "is_new": user_id is not None and req.email is not None}


@router.get("/users/{user_id}", dependencies=[Depends(require_api_key)])
def get_user(user_id: str) -> dict[str, Any]:
    if not db.client:
        raise HTTPException(503, "Database unavailable")
    r = db.client.table("user_profiles").select("*").eq("id", user_id).limit(1).execute()
    if not r.data:
        raise HTTPException(404, "User not found")
    return r.data[0]


@router.post("/intake")
async def intake_chat(req: IntakeRequest) -> IntakeResponse:
    """Advance the AI intake conversation by one turn."""
    # Build messages: system + conversation so far
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        *req.conversation,
    ]

    # Prefer Anthropic (Claude) for quality, fall back to DeepSeek
    ai_content, stage = await _call_ai(messages)

    return IntakeResponse(
        role="assistant",
        content=ai_content,
        stage=stage,
        user_id=req.user_id,
    )


@router.post("/submit")
def submit_inquiry(req: SubmitRequest) -> dict[str, Any]:
    """Finalize intake and save for attorney review."""
    if not db.client:
        raise HTTPException(503, "Database unavailable")

    now = datetime.now(UTC).isoformat()
    inquiry_id = str(uuid.uuid4())

    db.client.table("attorney_inquiries").insert({
        "id": inquiry_id,
        "user_id": req.user_id,
        "conversation": req.conversation,
        "intake_summary": req.intake_summary,
        "status": "pending",
        "created_at": now,
    }).execute()

    return {
        "inquiry_id": inquiry_id,
        "status": "pending",
        "message": "Your case has been submitted. An attorney will review it within 1-2 business days.",
    }


# ── Helpers ─────────────────────────────────────────────────────────────────────

async def _call_ai(messages: list[dict]) -> tuple[str, str]:
    """Call AI for intake response. Returns (content, stage)."""
    # Try Anthropic first
    if _ANTHROPIC_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": _ANTHROPIC_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5",
                        "max_tokens": 300,
                        "system": messages[0]["content"] if messages[0]["role"] == "system" else "",
                        "messages": [m for m in messages if m["role"] != "system"],
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["content"][0]["text"]
                    stage = _parse_stage(text)
                    return text, stage
        except Exception as e:
            logger.warning("Anthropic intake call failed: %s", e)

    # Fallback: deepseek
    if _DEEPSEEK_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {_DEEPSEEK_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "max_tokens": 300,
                        "temperature": 0.7,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    stage = _parse_stage(text)
                    return text, stage
        except Exception as e:
            logger.warning("DeepSeek intake call failed: %s", e)

    # Hard fallback — no AI available
    return (
        ("Thank you for reaching out. I'm having trouble connecting right now. "
        "Please try again in a moment, or call the Florida Bar referral line at "
        "800-342-8011 for immediate assistance."),
        "greeting",
    )


def _parse_stage(text: str) -> str:
    """Extract stage from first line if present."""
    first_line = text.split("\n")[0].strip().lower()
    for stage in ("greeting", "case_type", "details", "contact", "summary", "done", "urgent"):
        if stage in first_line:
            return stage
    return "details"
