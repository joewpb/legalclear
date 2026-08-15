# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S3-4 (AUDIT_FINDINGS.md §6):
"Deadline computed without closures on fetch failure — `pipeline.py:99-112`. A
silently-wrong legal deadline is the product's worst-case failure. Proposed fix:
escalate/refuse computation (or mark assumption_disclosure) when closure fetch fails.
Blast radius: deadline pipeline tests. Indep: yes."

DECISIONS.md Group B: S3-4 (closure fetch failure must not silently compute).

## Scope resolution (authoritative for this run)
- Read `backend/deadline/pipeline.py` (the closure-fetch section cited above), the
  deadline router/agent that consumes the pipeline, and the existing deadline tests
  (`backend/tests/` — find them; also `backend/deadline/` internals as needed).
- The fix must eliminate the silent path: when the court-closures fetch fails, the
  computation must NOT proceed to produce a deadline as if closures were known.
- Choose between the two options the triage offers, by THIS rule: if the existing
  response/pipeline already carries a field like `assumption_disclosure` (or an
  escalation/flagging concept you can populate without changing the public API shape),
  use it — mark the result as computed-without-closures AND make that fact visible to
  the caller. If no such field exists and adding one would change the public response
  shape, REFUSE the computation with an explicit error instead. State which option you
  chose and why in your report. Do NOT change public API response shapes.
- Do not change the deadline math itself. No LLM in date arithmetic.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- Missing data must never silently produce a legal result. Fail or flag, never guess.
- uv for Python. No pip, no poetry.

## Done means
1. A test that fails before and passes after (simulate the closure-fetch failure). Show
   both runs.
2. Minimal diff.
3. Full suite green (CI-scope command, exact):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py
4. One paragraph: what was wrong, what changed, what could regress.
