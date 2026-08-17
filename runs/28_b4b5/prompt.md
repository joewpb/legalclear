# TASK: B4b-5 — wills_trusts + small_claims: typed disclaimer SSE event. Two surfaces.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-5-wt-sc-typed (already checked out).

## Context
Same treatment as the just-completed B4b-4 (criminal + discovery — commit 61f3326 on
fix/b4b-4-criminal-discovery; read that diff as the reference pattern; its tests are
backend/tests/test_criminal_disclaimer_sse.py and test_discovery_disclaimer_sse.py).
The streaming generators may live in agent modules rather than the router files
(routers forward agent chunks). Find where each stream actually emits:
- backend/src/api/routers/wills_trusts.py — SSE at :64
- backend/src/api/routers/small_claims.py — SSE at :104

## Job
1. Success path: typed `event: disclaimer` + `data: {"disclaimer": <text>}` frame
   emitted once per stream, using the deterministic get_disclaimer(language) — never
   model-derived text. Keep any embedded disclaimer field in payload JSON unchanged.
2. Error paths: every error exit of each stream must emit the typed disclaimer event
   before its terminal error frame. If an error path is bare, add the emission.
3. Tests (red→green): for each surface assert the raw SSE bytes contain
   `event: disclaimer` round-tripping to {"disclaimer": ...} on success AND error
   (mock the agent for errors). Follow the B4b-4 test pattern exactly.
4. Do not change payload JSON shape, agent contract, or non-disclaimer frames.

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
- Report: file:line of every emission point (success + each error path), test
  evidence, suite count.
