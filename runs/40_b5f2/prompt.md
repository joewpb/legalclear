# TASK: B5-f2 — the user-supplied record wins AS A UNIT. Two contracts.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b5-f2-user-supplied-unit (already checked out).

## Background — three sequential bugs, same root shape
Verified live: the date didn't win (B5-f fixed), the ordering didn't let it win
(B5-f fixed), and NOW the method doesn't win: doc 56703e4b, PUT posted
(08-10 posting, 08-12 mailing) recomputed due 2026-08-17 — computed from the
posting date via the conservative unknown-method path, because the recompute
used the freshly EXTRACTED service_method ("unknown") instead of the persisted
user_service_method ("posted"). Later-of (Decision 6) never fired.

## Contract 1 — single consultation point
Do NOT patch the method individually. Refactor the recompute path
(backend/deadline/pipeline.py run_deadline_pipeline) so it reads the persisted
user-supplied record ONCE, as a unit — user_service_date, user_service_method,
clerk_mailing_date — and overrides every corresponding extracted value at
compute time. When service_date_provenance == 'user_supplied', no extracted
value for ANY of those fields may reach the computation. Structure it so
adding a future user-supplied field requires no new override logic (e.g. a
unit record object that the compute step consumes wholesale rather than
per-field ifs).

## Contract 2 — supersede stale rows
Recompute currently inserts new deadline rows without superseding old ones —
doc 56703e4b carries conflicting 08-17 and 08-21 rows. A recompute must
supersede or replace prior deadline rows for that document (same trigger
event), not accumulate. Implement the supersede semantics in the pipeline
(delete-then-insert or equivalent within the recompute path). Do NOT write
to prod — the doc 56703e4b cleanup happens as part of live verification.

## Tests — PIPELINE level (function-level tests have passed while these bugs lived)
In backend/tests/test_deadline_pipeline.py style (fake db + monkeypatched
extract), exercise run_deadline_pipeline end-to-end:
1. posted + persisted user method "posted" (posting 08-10, mailing 08-12) with
   the extractor returning service_method "unknown" → later-of FIRES: due date
   computed from 08-12 (~2026-08-19), trace contains 08-12.
2. Two recomputes with different user-supplied dates → exactly ONE live
   deadline row remains (supersede).
3. provenance user_supplied → no extracted date or extracted method appears
   anywhere in the computation trace.
Green or STOP.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 329/1 — must not drop.

## Rules
- uv only. Backend only. No prod writes, no migrations executed, no secrets.
- Report: file:line of the unit-record consultation, the supersede mechanism,
  the three pipeline regression tests with asserted dates, suite count.
