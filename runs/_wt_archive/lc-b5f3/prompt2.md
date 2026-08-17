# TASK: B5-f3 — RE-DISPATCH. Finish the facts-table migration to GREEN.
Prior run (fix/b5-f3-service-facts-table) exhausted 40 turns mid-implementation
and left the suite RED — 8 failures. The design is settled; your job is to
finish it. The design is NOT yours to change.

Repo: backend/ is this repo. Worktree: /home/joe/code/lc-b5f3 (branch checked
out). The working tree holds the prior run's uncommitted edits — keep the
good parts, fix the broken parts.

## State of the tree (verified)
- db.py has the document_service_facts helpers (get_document_service_facts
  ~line 386, upsert_document_service_facts ~line 408).
- deadline.py (PUT service-date) has docstrings pointing at the facts table.
- pipeline.py is partially rewired.
- FAILING (8): test_anchor_gate.py (4: issuance-never-stands-in, unknown-
  event-not-valid, service-date-computes-normally [TypeError], rendition-
  anchor-gates), test_deadline_recompute_escalation.py (3: supply/edit/
  posted-with-mailing recompute), test_pipeline_no_epoch.py (1).
  The TypeError + others are the same class as before: old test fakes lack
  the new db methods (get_document_service_facts/upsert_document_service_
  facts) the pipeline now calls. Update the fakes to mirror the real db API
  (return None / record writes), and finish the pipeline wiring.

## Finish, in order
1. PUT endpoint writes to document_service_facts (upsert by document_id) —
   NOT to trigger_events. (db.py helpers exist — use them.)
2. Recompute reads the facts row ONCE as a unit BEFORE any event write, and
   overrides every extracted value (B5-f2's UserSuppliedServiceRecord /
   _resolve_user_supplied structure must now source from the facts table).
3. trigger_events user_* columns: stop reading AND writing them in
   production paths (deprecated, not dropped). FOLLOW_UPS.md note (already
   drafted by the prior run — check it, keep or fix it).
4. Preserve supersede semantics (delete-then-insert deadlines).
5. Fix the 8 failing tests (update old fakes with the new methods; do not
   weaken assertions — adapt harnesses to the new API).
6. Required new pipeline-level tests (if the prior run didn't finish them):
   - posted + user method, extractor unknown → later-of fires, trace 08-12
   - full recompute cycle → facts row UNCHANGED afterward
   - provenance user_supplied → no extracted date/method in trace
   - second recompute, different date → exactly one live deadline row

## Verification
cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 332/1 — must not drop. GREEN or STOP.
