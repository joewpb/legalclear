# TASK: B4 Dispatch 1 — frontend SSE client tolerance. Single surface: frontend.

Repo: frontend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4a-sse-tolerance (will be created for you — run from repo root, the
work is in frontend/src only).

## Why this ships FIRST
The backend will soon emit a TYPED disclaimer SSE event (B4 Dispatch 2). The client's
SSE parser currently cannot tolerate unknown event types: if the backend emits the new
event before the client is updated, the disclaimer would vanish from the UI — a UPL
regression worse than the status quo. Client tolerance must land before the backend
change.

## Fix
1. Make the SSE parser tolerate unknown event types gracefully (ignore them, log at
   debug, never crash the stream, never drop the rest of the payload).
2. Render the disclaimer as a TYPED event: locate every current disclaimer rendering
   path in the streaming UIs (Criminal explainer, Discovery explainer, deadline/UPL
   surfaces, attorney-referral chat) and make the client handle a typed disclaimer
   event (e.g. event: disclaimer) when present, while keeping full backward
   compatibility with the current inline-text rendering until the backend ships.
3. No behavior change for existing events.

## Verification
- frontend has no unit-test runner by convention — verify with: cd frontend && npm run
  build 2>&1 (must exit 0). ALSO add/extend whatever lightweight check exists in
  frontend/package.json scripts (e.g. lint) and run it.
- Report file:line of the parser change and the disclaimer rendering paths touched.
- No backend changes. No migrations. No secrets.

## Rules
- uv only for python (not used here); npm for frontend. Do not commit secrets.
- Report: what changed (file:line), build evidence, and the explicit backward-
  compatibility guarantee.
