# Phase G, group 2 — push_tokens removal (Decision 9 deferred the mobile app)

Repo: joewpb/legalclear. Worktree: ~/code/lc-g2 (branch fix/g2-push-tokens-remove, cut from origin/main 849c4a5).

## Context (orchestrator pre-verified 2026-08-17)

- backend/src/memory/db.py:83-98 — save_push_token() writes table "push_tokens".
- backend/src/api/routes.py:253-254 — add_push_token() helper calling save_push_token.
- mobile/ is an EMPTY directory (ls shows only . and ..).
- backend/src/api/routers/reminders.py:68,85 reads users.expo_push_token — that is
  the users TABLE column, a DIFFERENT thing. DO NOT TOUCH reminders.py.
- No test or script references push_token (orchestrator grep).

## Part 1 — verify before touching (report-first)

1. Grep the whole repo (backend/src, frontend/src, scripts/, backend/tests/, evals/)
   for: add_push_token, save_push_token, push_tokens, push-token, push_token.
   Exclude __pycache__. For every hit, label: LIVE CALLER / dead-end reference /
   same-name-different-thing (e.g. reminders.py expo_push_token).
2. Confirm no HTTP route decorator references push tokens (the endpoint appears to
   have been removed already — only the helper + db method remain). State VERIFIED
   or INFERRED.
3. If you find ANY live caller — STOP, write findings to prompt-answer.md, no edits.

## Part 2 — delete (only if zero live callers)

1. Remove add_push_token() from backend/src/api/routes.py (lines ~253-254).
2. Remove save_push_token() from backend/src/memory/db.py (lines ~83-98) and any
   now-unused import it leaves behind (check ruff-style: only delete an import if
   nothing else in the file uses it — verify with grep before removing).
3. Delete the empty mobile/ directory (rmdir mobile).
4. Run the suite with the CI-scope ignores from .github/workflows/pytest.yml:
   uv run pytest tests/ -q <the exact --ignore= list>. Baseline: 352 passed, 1 skipped.
   Any NEW failure caused by your change: fix or revert.
5. Report: files changed, suite result, caller-verification detail.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network (no curl,
no WebFetch). No railway/supabase commands. Edit in place — the orchestrator commits.
DO NOT touch reminders.py or anything in backend/src/api/routers/. DO NOT author any
SQL migration (the DB table drop is a separate held item — out of your scope).
