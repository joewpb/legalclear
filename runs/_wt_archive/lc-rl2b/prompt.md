# Dispatch RL-2B — rate-limit coverage: intake, chat, forms

Repo: joewpb/legalclear. Worktree: ~/code/lc-rl2b (branch fix/rl2b-limits, cut from origin/main — RL-1 XFF key already merged).

## Task

Add slowapi rate limits (10/minute — matching the existing convention) to the
LLM-calling routes in these three routers. Shared limiter:
`from src.api.limiter import limiter`.

Per router:
1. **intake.py** — no limiter import. The LLM call is the inline Haiku
   classifier in POST `/intake`. Add the import + decorator above that route.
2. **chat.py** — no limiter import. Limit POST `/{module}` (:57) — the
   ChatExpertAgent LLM route.
3. **forms.py** — no limiter import. Grep for the suggest route that uses
   `SUGGEST_MODEL` (inline LLM). Limit that route. The list/search/facets
   routes are deterministic DB reads — do NOT limit them (report this split).

Do NOT change any existing limit value. Do NOT touch routes.py, limiter.py, or
any other router. Decorator directly above the route decorator
(discovery.py:16-17 convention).

## Verify

Run the suite with the CI-scope ignores from .github/workflows/pytest.yml
(baseline 352 passed, 1 skipped + RL-1 tests). Zero NEW failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network. No
railway/supabase. Edit in place — orchestrator commits. Final answer: per-route
changes with file:line, routes skipped with reason, suite result, turn count.
