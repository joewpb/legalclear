# TASK: Fix ONE sub-defect of triage S3-5. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S3-5 (AUDIT_FINDINGS.md §6) — SUB-ITEM c ONLY:
"UPL date-parse → silent pass — `upl.py:216`. A malformed date silently skips a
fatal-deadline escalation trigger. Proposed fix: treat unparseable date as
escalate-worthy."

This run covers ONLY `backend/src/core/upl.py` (the `:216` swallow site in the
escalation check). The intake and discovery sub-items are separate dispatches — do not
touch `routers/intake.py` or `agents/discovery_motion.py`.

## Scope resolution (authoritative for this run)
- Read `backend/src/core/upl.py` fully, plus its direct callers (the escalation checks
  are invoked from agent/route paths — find them) and the existing UPL tests
  (`backend/tests/` — find them; `test_upl.py`, `test_pc_upl.py` likely exist).
- The failure mode: a malformed/unparseable date in the escalation check is swallowed,
  so a deadline that SHOULD trigger fatal-deadline escalation is skipped silently.
- Fix direction per the triage: treat an unparseable date as escalate-worthy (fail
  toward escalation, never toward silence). Make the smallest change that does this.
- Keep the public behavior of well-formed dates identical. No new event shapes, no
  frontend changes.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- Silent swallows are bugs. Fail toward escalation, never toward silence.
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
