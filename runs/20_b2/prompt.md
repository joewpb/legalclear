# TASK: B2 — S3-5d. Fix pipeline insert swallows. Single surface, one job.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b2-s3-5d-insert-swallow (already checked out).

## Defect (verified from triage, file:line is from the pre-B1 main — re-locate if
## offsets moved; the swallowing behavior itself is the target)
backend/deadline/pipeline.py:209,245: DB insert errors for trigger_events and deadlines
are swallowed — the except branch logs (or not) and the endpoint still returns 200 with
deadlines_written counting as if the insert happened (or as 0 with no error). Same class
as the Group B silent-failure fixes (S3-5a/b/c, all merged): the caller cannot tell
"endpoint never called" from "called and failed silently".

## Fix
- Trigger-event insert failure and deadline insert failure must surface. Follow the
  pattern established by the merged S3-5a (intake: total outage → 503) and S3-5c
  (escalation instead of silent pass): choose the honest semantics — if the DB write
  fails, the endpoint must NOT claim success. Concretely: raise/log with escalation
  fields, or 500/503, consistent with the existing escalation shape in pipeline.py.
  Do not invent a new pattern — mirror S3-5a/S3-5c (read them: routers/intake.py,
  core/upl.py) and match the escalation_reason conventions B1's work also uses.
- Preserve: partial success must be reported truthfully (e.g. trigger written but
  deadline insert failed → state that exactly in the response and escalation fields).

## Tests (red→green)
- At least one test proving a mocked DB failure no longer yields a 200 that claims the
  write happened.
- Keep every existing test green. Full CI-scope suite command (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
- NOTE: this branch was cut from main WITHOUT B1's changes (B1 lives on
  fix/b1-s2-7-date-anchors). If your edits land in the same regions of pipeline.py
  that B1 changed (the anchor gate around lines 150-170 there), that is EXPECTED and
  fine — do not reconcile anything, just do your job on this branch and note the
  overlap in your report.

## Rules
- uv only. No migrations, no DDL, no prod writes, no secrets.
- Report: the exact failure semantics chosen, file:line of the fix, test evidence
  (red→green), suite count, and the B1-overlap note if it applies.
