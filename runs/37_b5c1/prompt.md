# TASK: B5-c1 — service-date endpoint + validation ONLY. No recompute. No escalation.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-c1-service-date-endpoint (already checked out).

## Context
- Migration APPLIED in prod: trigger_events now has user_service_date (date),
  user_service_method (text), service_date_provenance (text not null default
  'extracted', check in ('extracted','user_supplied')).
- B5-b (fix/b5-b-service-date-core, 8edce55, UNMERGED) built the DB-layer helpers
  (db.py: set_user_service_date etc.) and pipeline consumption. Your branch starts
  from MAIN — the helpers are NOT on main. Do not import them. Write your endpoint
  against the existing db access pattern in deadline.py and note the seam in your
  report. Your tests must pass against main today.
- The abandoned branch wip/b5-c-abandoned exists for design reference only — do not
  build on it.

## Job — ONE contract: endpoint + validation. Nothing else.
In backend/src/api/routers/deadline.py (match its existing path/API-key patterns):
1. Endpoint to supply/update the service date for a document:
   PUT /api/deadline/{document_id}/service-date
   Body: { "service_date": "YYYY-MM-DD", "service_method": "personal" }
   method enum: personal | substitute | posted | mail | eservice | unknown
   For posted: clerk_mailing_date field is REQUIRED in the body — 422 without it.
   (clerk_mailing_date accepted but NOT persisted by this dispatch — persistence
   of it belongs to a later slice; just validate its presence and format here.
   State that explicitly in the report.)
2. Writes: user_service_date = service_date, user_service_method = service_method,
   service_date_provenance = 'user_supplied' — ALWAYS. There is NO code path in
   this endpoint that writes 'extracted'.
3. Validation ONLY: date sanity (valid date, not absurd: 2000-01-01..today+7d),
   method enum, posted-requires-mailing-date 422. No recompute, no deadline
   writes, no escalation contract — that is B5-c2's job. Your response: the
   stored values + {recompute: "pending"} placeholder status field, documented.
4. Tests (red→green): valid upsert writes all three fields with
   provenance=user_supplied; bad date 422; bad method 422; posted without
   mailing date 422; posted WITH mailing date accepted. Use the repo's existing
   router-test mock patterns (see test_deadline_pipeline.py's fake recorder).
   GREEN tests or STOP — do not leave red.

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
- uv only. Backend only. No prod writes, no migrations executed, no secrets.
- Report: file:line of the endpoint, response schema, the B5-b seam note, the
  clerk_mailing_date persistence note, test evidence, suite count.
