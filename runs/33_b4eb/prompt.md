# TASK: B4e-b — Decision 5 conditional error-path disclaimers: wills_trusts + small_claims.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4e-b-wtsc-conditional (already checked out).

## Context
Decision 5 (DECISIONS.md): an error carrying no substantive content needs no
disclaimer; an error AFTER substantive content has been emitted MUST carry the typed
disclaimer. Current state (B4b-5, merged): both agents emit the typed
`event: disclaimer` UNCONDITIONALLY before every error frame. Make it conditional —
identical work to B4e-a (criminal/discovery), same pattern.

## Job (2 call sites: wills_trusts.py + small_claims.py)
1. Track whether any substantive content (non-disclaimer, non-keepalive frame) has
   been emitted so far.
2. On error exit: emit the typed `event: disclaimer` frame ONLY if substantive
   content was already emitted. Otherwise just the terminal error frame.
3. Keep payload shapes, embedded disclaimer fields, success paths identical.
4. Tests (red→green): per agent — (a) error AFTER content → disclaimer event present,
   (b) error BEFORE any content → disclaimer ABSENT, terminal error present. Update
   backend/tests/test_wills_trusts_disclaimer_sse.py and
   backend/tests/test_small_claims_disclaimer_sse.py to the conditional truth.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 275/1 — must not drop.

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: file:line of each conditional, test cases, suite count.
