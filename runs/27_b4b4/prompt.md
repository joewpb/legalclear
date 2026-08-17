# TASK: B4b-4 — criminal + discovery: typed disclaimer SSE event. Two routers.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-4-criminal-discovery (already checked out).

## Context
Two streaming routers whose disclaimer reaches the client embedded inside agent
payload chunks (the agents append `disclaimer` via get_disclaimer into the JSON they
stream). The b4a frontend now handles typed `event: disclaimer` SSE events. Convert
these two routers to emit the disclaimer as a typed event, and cover the ERROR path.

- backend/src/api/routers/criminal.py — SSE at :62
- backend/src/api/routers/discovery.py — SSE at :35

## Job
1. Success path: emit a typed `event: disclaimer` + `data: {"disclaimer": <text>}`
   frame in each stream. The canonical text comes from the payload/agent output that
   already contains the disclaimer field — extract and emit it typed; KEEP the
   embedded field inside the JSON chunks too (backward compat — the b4a frontend
   prefers the typed event, older payloads keep working).
2. Error path: if the stream errors mid-flight, emit the typed disclaimer event (and
   a terminal error frame per the existing error shape) so a UPL disclaimer is
   ALWAYS present on error exits. If an error path today terminates WITHOUT any
   disclaimer, that is the gap to fix — add the typed disclaimer emission there.
   (deadline.py's bare-error gap is a separate logged finding — here, FIX the
   streaming error path, don't just log it.)
3. Do not change the payload JSON shape, the agent contract, or any non-disclaimer
   frame.
4. Tests (red→green): for each router, assert the raw stream bytes include
   `event: disclaimer` with a round-trippable {"disclaimer": ...} payload on BOTH
   success and error paths (mock the agent for the error case). Reuse the pattern
   from backend/tests/test_forms_disclaimer_sse.py (B4b-3, merged earlier today).

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 249/1 — must not drop.

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: file:line of every emission point added/changed, success+error test
  evidence, suite count.
