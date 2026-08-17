# Phase G, group 4 — trigger_events user_* columns: remove dead helpers + author drop migration

Repo: joewpb/legalclear. Worktree: ~/code/lc-g4 (branch fix/g4-drop-user-columns, cut from origin/main 849c4a5).

## Context

B5-f3 moved user-supplied service facts to the document_service_facts table. The
trigger_events columns user_service_date / user_service_method /
service_date_provenance are deprecated — documented in FOLLOW_UPS.md ("B5-f3 —
trigger_events.user_* columns deprecated, not dropped"). Orchestrator pre-grep:
the ONLY readers are the deprecated helpers themselves in
backend/src/memory/db.py (~lines 434-520: get_user_supplied_service_date +
set_user_supplied_service_date, marked DEPRECATED), which have ZERO callers
anywhere (only their own error-log lines). Zero test references.

## Part 1 — verify before touching

1. Grep backend/src, backend/tests, scripts/ for: user_service_date,
   user_service_method, service_date_provenance, get_user_supplied_service_date,
   set_user_supplied_service_date. Exclude __pycache__ and supabase/migrations/.
   For every hit label: dead-helper-internal / LIVE READER / test-fake / migration.
2. Grep for document_service_facts usage to confirm the replacement path is what
   production code actually uses (sanity check — report only).
3. If any LIVE READER exists (outside the deprecated helpers) — STOP, write to
   prompt-answer.md, no edits.

## Part 2 — remove helpers + author migration (only if zero live readers)

1. Delete the deprecated helper block in backend/src/memory/db.py: the
   get_user_supplied_service_date and set_user_supplied_service_date methods and
   their surrounding DEPRECATED docstring region (~lines 430-520; read the actual
   boundaries — delete the whole contiguous block of these two methods). Do not
   delete anything else in db.py.
2. Create supabase/migrations/20260817010000_g_drop_trigger_events_user_columns.sql
   with EXACTLY this content (idempotent, rides CI on merge-push per Joe):
   -- Phase G (2026-08-17): drop trigger_events.user_* columns deprecated by B5-f3.
   -- User facts live on document_service_facts; zero readers remain after the
   -- deprecated db.py helpers were removed. Idempotent.
   ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS user_service_date;
   ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS user_service_method;
   ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS service_date_provenance;
3. Run the suite with the CI-scope ignores from .github/workflows/pytest.yml.
   Baseline: 352 passed, 1 skipped. Any NEW failure: fix or revert.
4. Report: grep evidence, files changed, suite result.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network. No
railway/supabase. Edit in place — orchestrator commits. The migration is AUTHORED
ONLY — do not attempt to run or apply it anywhere. Do not touch
document_service_facts or its migration. Do not modify any other migration file.
