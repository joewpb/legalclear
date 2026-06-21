"""Chat router — conversational expert endpoint.

POST /api/chat/{module}
  - module: small_claims | criminal_procedure | police_report |
            discovery_motion | property_casualty
  - Body: { "message": string, "session_id": string }
  - Returns: SSE streaming response

Response is a stream of JSON chunks:
  - {"chunk": "text fragment"}   — streaming content
  - {"disclaimer": "..."}        — required disclaimer
  - {"done": true}               — end of stream
  - {"error": true, "message": "...", "disclaimer": "..."} — on failure
"""

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.chat_expert import ChatExpertAgent, VALID_MODULES

router = APIRouter(prefix="/api/chat")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_expert = ChatExpertAgent()


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's question")
    session_id: str = Field(..., min_length=1, description="Chat session identifier")
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

    async def _stream():
        async for chunk in _expert.chat(
            module=module,
            message=body.message,
            session_id=body.session_id,
            language=body.language,
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
