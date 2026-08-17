# TASK: B4b-3 — forms.py disclaimer: untyped chunk → typed event. Single router.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-3-forms-typed (already checked out).

## Context
backend/src/api/routers/forms.py currently emits the disclaimer as a plain data
chunk: `yield f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"` (forms.py:528
area). The frontend (b4a, merged) now understands typed SSE events: lines like
`event: disclaimer\ndata: {...}\n\n`. Convert this router to the typed form.

## Job
1. Change the disclaimer emission to typed SSE:
   `event: disclaimer` + `data: {json}` payload, per the SSE spec (blank line
   terminator). Keep the payload shape ({disclaimer: ...}) so the b4a frontend handler
   works unchanged.
2. Keep full backward compatibility: the OTHER data chunks in the same stream must not
   change shape. If there are multiple disclaimer emission points (empty-stream path,
   stream path, error path — check all), convert each. If the error path has none,
   do NOT add one (that is a B4-wide decision, see FOLLOW_UPS) — just report it.
3. Frontend note: FormsFinderFL.tsx (b4a) already handles event=disclaimer — verify
   its expected payload key matches what you emit (check frontend/src/pages/
   FormsFinderFL.tsx and frontend/src/lib/sse.ts, adjust the EMITTED payload key only
   if the frontend expects something else; do not touch frontend files).
4. Tests: update/extend backend tests that assert the forms stream output. Assert the
   raw bytes contain "event: disclaimer" and the data payload round-trips. Red→green.

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
- uv only. Backend only (frontend read-only reference). No migrations, no secrets.
- Report: file:line of the emission change(s), test evidence, suite count, and the
  error-path status note.
