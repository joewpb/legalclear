# Dispatch RL-2A — rate-limit coverage: criminal, police_report, expungement

Repo: joewpb/legalclear. Worktree: ~/code/lc-rl2a (branch fix/rl2a-limits, cut from origin/main — the RL-1 XFF key must already be merged).

## Task

Add slowapi rate limits (10/minute — matching the existing convention) to the
LLM-calling routes in these three routers. The shared limiter is
`from src.api.limiter import limiter` (already XFF-fixed by RL-1).

Per router:
1. **criminal.py** — limiter already imported (:11). Add
   `@limiter.limit("10/minute")` above the `/explain` route (:48).
2. **police_report.py** — no limiter import. Add it, then limit the LLM routes:
   `/analyze` and the legacy `/analyze/batch` (both make LLM calls — verify
   with grep before decorating; limit whichever of the two actually call the
   LLM, report if one is dead).
3. **expungement.py** — no limiter import. Grep for LLM calls: eligibility uses
   `ExpungementAgent`; the packet generate path may be deterministic. Limit
   every route that makes an LLM call; report which were skipped and why.

Do NOT change any existing limit value. Do NOT touch routes.py, limiter.py,
or any other router. Follow the existing decorator placement convention
(decorator directly above the route decorator, as in discovery.py:16-17).

## Verify

Run the suite with the CI-scope ignores from .github/workflows/pytest.yml
(baseline 352 passed, 1 skipped + RL-1's new tests). Zero NEW failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network. No
railway/supabase. Edit in place — orchestrator commits. Final answer: per-route
changes with file:line, any routes skipped with reason, suite result, turn count.
