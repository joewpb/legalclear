# TASK: Fix ONE sub-defect of triage S3-5. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S3-5 (AUDIT_FINDINGS.md §6) — SUB-ITEM b ONLY:
"Discovery risk-parse → silent pass — `discovery_motion.py:209`. Outages
indistinguishable from valid results. Proposed fix: distinguish error payloads; log at
error + emit error event."

This run covers ONLY `backend/src/agents/discovery_motion.py` (the `:209-210` swallow
site: the deterministic risk-score event is dropped on parse failure, so the user gets
an analysis with no risk score and no error). The intake and upl sub-items are separate
dispatches — do not touch `routers/intake.py` or `core/upl.py`.

## Scope resolution (authoritative for this run)
- Read `backend/src/agents/discovery_motion.py`, the risk-score parse site, and the
  streaming contract on the client (`frontend/src/pages/DiscoveryMotionAnalyzer.tsx` —
  remember from the audit that this client whitelists exactly ONE typed event,
  `type === "risk_analysis"`; anything else accumulates into the explanation JSON and
  can corrupt the final parse). A fix that emits a NEW event shape could break the
  client — if the only safe channel is to log at error and carry on visibly, or to
  reuse the existing error-event shape the client already tolerates, do that.
- Goal: a parse failure must not silently vanish. Minimum bar: log at error with the
  raw cause; better: surface a visible error to the user through a channel the client
  already handles. Do NOT invent a new event type unless you also verify the client
  tolerates it — and remember you cannot edit the frontend in this run unless the
  response shape would break the shipped caller, in which case STOP and report.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- Silent swallows are bugs. Fail or flag, never vanish.
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
