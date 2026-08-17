# TASK: B5-b — DB layer + pipeline consumption: user-supplied service date + posted bucket.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-b-service-date-core (already checked out).

## Background
Decision 2 (DECISIONS.md): service date is ASKED of the user, stored with provenance
user_supplied, never extracted. Decision 6: posted service (§ 48.183) computes from
the LATER of posting date and clerk-mailing date; mailing date unknown → escalate,
never compute from posting alone.

## Migration (Joe is applying it to prod NOW; do not apply anything yourself)
supabase/migrations/20260815000000_b5_service_date_capture.sql adds to
public.trigger_events: user_service_date date (nullable), user_service_method text
(nullable), service_date_provenance text not null default 'extracted' with check
('extracted','user_supplied'). Reference it; never execute it.

## Job
1. DB layer (backend/src/memory/db.py): read/write helpers for user_service_date,
   user_service_method, service_date_provenance on trigger_events. Read path: when
   fetching a document's trigger events, return the provenance alongside the date.
2. Pipeline consumption (backend/deadline/pipeline.py + compute.py):
   - When a trigger event has user_service_date + provenance='user_supplied', that
     date IS the served anchor for rules requiring ("served",). The extracted
     event_date must NOT be substituted back in for that rule (Decision 2:
     user-supplied wins; never recompute from the extracted date once the user has
     supplied one).
   - Decision 6 bucket: add SERVICE_POSTED (or reuse/extend the existing constants —
     check compute.py's SERVICE_* set) as its own bucket. For posted service:
     effective date = LATER of posting date and clerk-mailing date. The clerk-mailing
     date comes from user input too (docket certificate) — if absent: ESCALATE with
     a clear reason; DO NOT compute from the posting date alone. Remove posted from
     the publication/unknown "earlier of personal or mail" path.
   - Unknown service method keeps its existing conservative behavior UNCHANGED.
3. Regression test (Job 3 — mandatory): posted service with posting date X and
   clerk-mailing date Y (Y > X) computes from Y, NOT from X, and NOT the earlier-of
   path. Plus: posted with mailing date missing → escalates, zero deadlines.
4. Tests for: user_supplied date wins over extracted for ("served",) rules;
   provenance check. Use the repo's existing test patterns (see test_deadline_pipeline.py,
   test_anchor_gate.py). Red→green.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 302/1 — must not drop.

## Rules
- uv only. Backend only. No migrations executed, no prod writes, no secrets.
- Report: file:line per change, the later-of logic, regression test evidence, suite
  count.
