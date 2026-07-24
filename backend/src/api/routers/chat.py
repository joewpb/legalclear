"""Chat router — conversational expert endpoint.

POST /api/chat/{module}
  - module: small_claims | criminal_procedure | police_report |
            discovery_motion | property_casualty | wills_trusts
  - Body: { "message": string, "session_id": string,
            "chat_history": [], "language": "en"|"es" }
  - Returns: SSE streaming response

Response is a stream of JSON chunks:
  - {"chunk": "text fragment"}   — streaming content
  - {"disclaimer": "..."}        — required disclaimer
  - {"done": true}               — end of stream
  - {"paywall": true, "message": "..."}  — paywall triggered at 5+ messages
  - {"error": true, "message": "...", "disclaimer": "..."} — on failure
"""


from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.chat_expert import VALID_MODULES, ChatExpertAgent

router = APIRouter(prefix="/api/chat")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_expert = ChatExpertAgent()


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ChatHistoryEntry(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's question")
    session_id: str = Field(..., min_length=1, description="Chat session identifier")
    chat_history: list[ChatHistoryEntry] = Field(
        default_factory=list,
        description="Prior messages in this session (role, content)"
    )
    language: str = Field(default="en", pattern="^(en|es)$")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/{module}")
async def chat_endpoint(module: str, body: ChatMessageRequest = Body(...)):
    """Stream a conversational response from the per-module expert."""

    if module not in VALID_MODULES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown module: {module}. Valid modules: {', '.join(sorted(VALID_MODULES))}",
        )

    # Count existing user messages from chat_history to enforce paywall
    user_message_count = sum(
        1 for entry in body.chat_history if entry.role == "user"
    )

    async def _stream():
        async for chunk in _expert.chat(
            module=module,
            message=body.message,
            session_id=body.session_id,
            language=body.language,
            chat_history=[e.model_dump() for e in body.chat_history],
            message_count=user_message_count,
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
