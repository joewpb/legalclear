# TASK: B4e-a — Decision 5 conditional error-path disclaimers: criminal + discovery.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4e-a-crimdisc-conditional (already checked out).

## Context
Decision 5 (DECISIONS.md): an error carrying no substantive content needs no
disclaimer; an error AFTER substantive content has been emitted MUST carry the typed
disclaimer. Current state (B4b-4, merged): both agents emit the typed
`event: disclaimer` UNCONDITIONALLY before every error frame — including errors that
fire before anything was streamed. That over-emission violates Decision 5's first
half. Make it conditional.

## Job (2 call sites: criminal_procedure.py + discovery_motion.py)
1. In each stream generator, track whether any substantive content has been emitted
   (any non-disclaimer, non-keepalive frame — e.g. the first explanation/chunk).
2. On error exit: emit the typed `event: disclaimer` frame ONLY if substantive
   content was already emitted. Errors with no prior content emit just the terminal
   error frame as today (minus the disclaimer).
3. Keep everything else identical — payload shapes, embedded disclaimer fields,
   success paths, frame order.
4. Tests (red→green): for each agent, (a) error AFTER content → disclaimer event
   present, (b) error BEFORE any content (mock failing on first call) → disclaimer
   event ABSENT, terminal error frame present. Extend the existing B4b-4 test files
   (backend/tests/test_criminal_disclaimer_sse.py,
   backend/tests/test_discovery_disclaimer_sse.py) — their unconditional-error
   assertions must be updated to the conditional truth.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 275/1 — must not drop below it minus nothing (this branch starts
from main at 275/1).

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: file:line of each conditional, the two test cases per agent, suite count.
