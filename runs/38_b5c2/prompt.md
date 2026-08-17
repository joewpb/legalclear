# TASK: B5-c2 — recompute + escalation contract. Single behavior pair.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-c2-recompute-escalation (already checked out).

## Context
- B5-c1 (fix/b5-c1-service-date-endpoint, b30986e, UNMERGED) built PUT
  /api/deadline/{document_id}/service-date with validation; its response carries
  {recompute: "pending"} placeholder. Your branch starts from MAIN — the endpoint
  is NOT on main. Your job is the recompute + escalation contract; implement it in
  the deadline router against the existing patterns, noting the B5-c1 seam
  (the endpoint will be wired to call your recompute path at merge time). Your
  tests must pass against main today.
- B5-b (fix/b5-b-service-date-core, 8edce55, UNMERGED) built pipeline consumption:
  user_service_date wins as the served anchor; SERVICE_POSTED computes
  later-of(posting, mailing); missing mailing date escalates with zero deadlines.
  Also NOT on main — do not import from it; implement your contract against main's
  pipeline entry points (run_deadline_pipeline) with mocks.
- Decision 2: "I don't know" escalates and does NOT compute; tell the user the
  return of service is filed with the clerk and the case docket shows the service
  date. Decision 6: posted + mailing date unavailable → escalate, no deadline.

## Job — TWO behaviors, nothing more:
1. **Recompute-on-supply / recompute-on-edit:** a service-date supply or update
   re-runs the deadline computation for the document (call the existing pipeline
   entry with the document's trigger events) and returns the refreshed deadlines.
   Implement as a router-level helper (e.g. _recompute_deadlines(document_id))
   usable by the c1 endpoint at merge time. Edit == same path (upsert semantics).
2. **I-don't-know contract:** when service_method is unknown OR (posted and
   clerk_mailing_date unavailable), the recompute path must:
   - store method as given (c1's endpoint already persists it)
   - return a structured escalation response (no deadline rows written/refreshed):
     guidance text per Decision 2 (return-of-service filed with the clerk; case
     docket shows the service date) + Decision 6 note for posted
   - write NO deadline row.
3. Tests (red→green): supply → recompute returns deadlines; edit → recompute
   returns updated deadlines; unknown → escalation payload + zero deadline writes
   (assert the DB write recorder saw no deadline inserts); posted-without-mailing →
   escalation + zero deadline writes. Mock per repo patterns. GREEN or STOP.

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
- Report: file:line of the recompute helper + escalation path, the escalation
  response schema, the B5-b/B5-c1 seam notes, test evidence, suite count.
