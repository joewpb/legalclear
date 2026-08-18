# Dispatch RL-2C — rate-limit coverage: case_law, attorney_referral, packet

Repo: joewpb/legalclear. Worktree: ~/code/lc-rl2c (branch fix/rl2c-limits, cut from origin/main — RL-1 XFF key already merged).

## Task

Add slowapi rate limits (10/minute — matching the existing convention) to
these three routers. Shared limiter: `from src.api.limiter import limiter`.

Per router:
1. **case_law.py** — no limiter import. VERIFY whether any route makes an LLM
   call: ADR-1 (docs/ADRS.md) states case-law retrieval is deterministic ILIKE
   (the old "inline Anthropic call case_law.py:72" claim was corrected as
   stale). Grep the file for anthropic/llm/model references. If a route DOES
   call the LLM, limit it. If NONE does: still add 10/minute to the search
   route for API protection and REPORT the finding explicitly ("no LLM call
   found — limit is API-protection only") — Joe wants this surfaced.
2. **attorney_referral.py** — no limiter import. Limit the LLM-calling routes:
   POST `/intake` (:145) and any fallback path that calls the model. The
   `/users` GET/POST are DB operations — verify and skip if no LLM (report).
3. **packet.py** — no limiter import. VERIFY whether any route makes an LLM
   call (orchestrator's grep found none — stripe + FileResponse only; the
   packet build appears deterministic). If no LLM call: still add 10/minute to
   the generate route for API protection and REPORT the no-LLM finding.

Do NOT change any existing limit value. Do NOT touch routes.py, limiter.py, or
any other router. Decorator directly above the route decorator
(discovery.py:16-17 convention).

## Verify

Run the suite with the CI-scope ignores from .github/workflows/pytest.yml
(baseline 352 passed, 1 skipped + RL-1 tests). Zero NEW failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network. No
railway/supabase. Edit in place — orchestrator commits. Final answer: per-route
changes with file:line, the LLM-verification findings per router, suite result,
turn count.
