# TASK: B5-f3 — move user-supplied service facts OFF pipeline-owned rows.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-f3-service-facts-table (already checked out, in worktree ../lc-b5f3).

## Root cause (four patches treated symptoms of this one design error)
user_service_date/user_service_method/clerk_mailing_date lived as columns on
trigger_events — rows the pipeline rewrites on every recompute, clobbering the
user's values. The date won (read before write) and the method lost.

## The fix
New table document_service_facts (APPLIED in prod; migration file
supabase/migrations/20260815000002_b5f3_document_service_facts.sql matches the
real schema): document_id (unique), service_date, service_method,
clerk_mailing_date, provenance (default 'user_supplied'). One row per document.
The pipeline never writes it.
1. PUT /api/deadline/{document_id}/service-date now writes to
   document_service_facts (upsert by document_id), NOT to trigger_events.
2. The recompute path reads that row ONCE as a unit (BEFORE any event write)
   and its values override every corresponding extracted value — preserve
   B5-f2's single-consultation-point structure (UserSuppliedServiceRecord /
   _resolve_user_supplied) and the supersede (delete-then-insert deadlines)
   semantics.
3. The trigger_events user_* columns are DEPRECATED: stop reading and writing
   them everywhere in the production path. Do NOT drop them (Phase G). Add a
   follow-up note to FOLLOW_UPS.md (you may append to that file — it is in
   your footprint for this one note only).

## Tests — pipeline level (in backend/tests/test_deadline_pipeline.py style)
- posted + persisted user method "posted" (08-10/08-12), extractor returns
  method "unknown" → later-of FIRES, due from 08-12 (~2026-08-19), trace
  contains 08-12.
- a full recompute cycle → the document_service_facts row is UNCHANGED
  afterward (this is the assertion that would have caught all four variants).
- provenance user_supplied → no extracted date or extracted method appears
  in the computation trace.
- second recompute with a different date → exactly ONE live deadline row.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 332/1 — must not drop.

## Rules
- uv only. Backend only. No prod writes, no migrations executed, no secrets.
- Report: file:line of the facts-table write path + the unit read, the
  deprecation points, the four regression tests, suite count.
