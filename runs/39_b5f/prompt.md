# TASK: B5-f — user-supplied service dates must WIN in the live pipeline. One contract.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-f-user-supplied-wins (already checked out).

## The defect (verified live in prod, 2026-08-15)
Eviction doc 56703e4b, extracted trigger: issued 2026-08-14.
- PUT personal, served 2026-08-10 → due 2026-08-21 computed from 08-14. Should be
  ~2026-08-17.
- PUT posted, posting 08-10 + mailing 08-12 → due 2026-08-21 from 08-14. Should be
  ~2026-08-19 (later-of per Decision 6).
run_deadline_pipeline re-extracts and computes from the extracted date regardless of
the user-supplied values. Decision 2: once the user supplies a service date, it WINS;
the extracted date is never used as the anchor for that rule.

## Scope — this and nothing else
1. In run_deadline_pipeline (backend/deadline/pipeline.py), the user-supplied anchor
   consultation must PRECEDE the anchor-gate/extraction-based computation. Currently
   the gate fires first (escalates or substitutes) and the Decision-2 block never gets
   consulted. Reorder so: for a rule requiring ("served",), if the DB has a
   user-supplied service date for the document (provenance user_supplied), that date
   IS the anchor. For posted service, anchor = later-of(user_service_date=posting,
   clerk_mailing_date); if clerk_mailing_date is missing → escalate per Decision 6,
   no deadline.
2. Persist clerk_mailing_date. Migration file exists:
   supabase/migrations/20260815000001_b5f_clerk_mailing_date.sql (adds
   trigger_events.clerk_mailing_date date). Joe applies it manually — do NOT execute
   it. Code against the column via db.py helpers and the endpoint: backend/src/api/
   routers/deadline.py PUT service-date must now WRITE clerk_mailing_date when
   supplied (not just validate+echo). Add db.py helper(s) as needed.
3. Posted computes from later-of(posting, clerk_mailing) per Decision 6 — the compute
   layer already has this (B5-b); make the PIPELINE feed it the persisted values.
No refactoring beyond the ordering fix. Nothing else.

## Tests — PIPELINE level, not function level
B5-b's unit tests pass while this bug is live — they test the compute function; the
defect is ordering in run_deadline_pipeline. New tests in the pipeline test file
(test_deadline_pipeline.py harness: _FakeDb + monkeypatched extract) must exercise
run_deadline_pipeline end-to-end with a user-supplied date present and assert the
anchor actually used:
- personal: fake extract yields an issued/served event 2026-08-14; fake db returns
  user_supplied 2026-08-10 → the deadline due date must be computed from 08-10
  (~2026-08-17), and the trace must reference 08-10.
- posted: user_supplied posting 08-10 + clerk_mailing 08-12 → due ~2026-08-19,
  trace references 08-12 (later-of).
- posted with NO clerk_mailing_date → escalates, zero deadlines.
Green or STOP.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 326/1 — must not drop.

## Rules
- uv only. Backend only. No prod writes, no migrations executed, no secrets.
- Report: file:line of the reordering, the persistence wiring, the three pipeline
  regression tests with asserted dates, suite count.
