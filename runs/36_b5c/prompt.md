# TASK: B5-c — API endpoints for user-supplied service date. Single router.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-c-service-date-api (already checked out).

## Background
Decision 2: user supplies the service date; stored with provenance user_supplied;
visible and editable; correction recomputes the deadline; "I don't know" escalates.
Decision 6: for posted service, capture posting date + clerk-mailing date; mailing
date unavailable → escalate, never compute from posting alone.

B5-b (dispatched in parallel, branch fix/b5-b-service-date-core) builds the DB-layer
helpers and pipeline consumption. NOTE the branch isolation: your tests must pass
against MAIN (B5-b not merged) — structure them so they assert YOUR endpoint
contract (validation, response shape, DB write calls via mocks), not the unmerged
pipeline internals. Use the repo's established mock patterns.

## Job — extend the deadline router (backend/src/api/routers/deadline.py)
1. New endpoint(s) to supply/update the service date for a document's trigger event:
   - PUT /api/deadline/{document_id}/service-date (or the closest existing path
     convention — match the router's current style). Body: service_date (YYYY-MM-DD),
     service_method (personal | substitute | posted | mail | eservice | unknown),
     clerk_mailing_date (optional; REQUIRED when method=posted — 422 without it).
   - Upsert semantics: write user_service_date, user_service_method,
     service_date_provenance='user_supplied' via the DB layer (mock in tests; the
     unmerged B5-b helpers are the intended target — import if present on main,
     otherwise write through the existing db pattern and note the seam).
   - Response: the stored values + a recompute trigger contract (recomputed
     deadlines, or an explicit {recompute: "deferred"} status field — choose the
     simpler honest contract and document it in the response schema).
2. "I don't know" path: service_method=unknown (or a dedicated flag) must NOT
   compute — return a structured escalation response with the Decision-2 guidance
   (return of service filed with the clerk; case docket shows the service date).
3. API key protection: match the router's existing dependency pattern (require_api_key
   where sibling endpoints use it).
4. Tests (red→green): validation (bad date, posted without mailing date), upsert
   writes provenance=user_supplied, unknown→escalation response, recompute contract.

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
- Report: file:line of endpoints, the response schema, the B5-b seam note, test
  evidence, suite count.
