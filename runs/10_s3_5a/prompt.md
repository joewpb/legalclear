# TASK: Fix ONE sub-defect of triage S3-5. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S3-5 (AUDIT_FINDINGS.md §6) — SUB-ITEM a ONLY:
"Intake failure → 200 `unknown` — `intake.py:196`. Outages indistinguishable from valid
results. Proposed fix: distinguish error payloads; log at error + emit error event."

This run covers ONLY `backend/src/api/routers/intake.py` (the `:196-200` swallow site).
The discovery-motion and upl sub-items are separate dispatches — do not touch
`agents/discovery_motion.py` or `core/upl.py`.

## Scope resolution (authoritative for this run)
- Read `backend/src/api/routers/intake.py`, its LLM call path, and its direct callers
  (frontend `HomeHub.tsx` calls `/api/intake` — read only enough to confirm the client's
  error handling; the fix must not break the shipped caller).
- The failure mode: both LLM attempts fail → the endpoint returns HTTP 200 with
  `module="unknown"`, so the client cannot distinguish an outage from an ambiguous
  input. Fix so the response distinguishes the two: either a non-200 status on total
  failure, or an explicit error field in the payload — whichever the existing response
  model and the shipped client can tolerate WITHOUT a public API shape change. If both
  options would break the shipped client, STOP and report instead of coding.
- Log at error level with the real cause.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- Outages must never look like valid answers.
- uv for Python. No pip, no poetry.

## Done means
1. A test that fails before and passes after. Show both runs.
2. Minimal diff.
3. Full suite green (CI-scope command, exact):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py
4. One paragraph: what was wrong, what changed, what could regress.
