# TASK: B5-f4 — one deadline row per governing rule. UNCONDITIONAL dedup.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-b5f4, branch fix/b5-f4-rule-dedup (checked out).

## The defect (verified live)
Each recompute writes the eviction answer deadline TWICE — once per extracted
trigger event. Extraction returns multiple events (issued 08-14, hearing
08-28), and the user-supplied anchor applies to every rule requiring
"served", so the hearing event also produces the same "Answer to Residential
Eviction Complaint" deadline. Two rows, two trigger_event_ids, identical due
date.

## The fix — do NOT condition on provenance
Dedup deadline writes on (document_id, governing_rule) — UNCONDITIONALLY,
not only when the anchor is user-supplied. A document has ONE instance of a
given legal obligation regardless of how many events extraction returns or
where the anchor came from. Four prior fixes in this lane were each scoped to
a condition and each missed the structure — do not add a fifth conditional
branch.

Where: the deadline write path in backend/deadline/pipeline.py (the loop
that inserts per deadline). Implementation choice is yours (e.g. a seen-set
per run keyed by governing_rule, upsert on a unique key, or replace-per-rule
before insert) — but it must be structural, not conditional on provenance.

If two events would produce genuinely DIFFERENT due dates under the same
rule, that is a conflict to ESCALATE (escalation_reasons + no second row),
not two rows to write. Report if you find such a case — do not invent one.

## Also — flag, do not fix
Extraction returned the hearing event duplicated. That is an upstream
extraction defect, outside this dispatch. Log it in FOLLOW_UPS.md with the
document id (56703e4b-a3b0-4ea6-aeb8-3334b7431274) and observed output.
No extractor changes.

## Tests — pipeline level (backend/tests/test_deadline_pipeline.py style)
- Multi-event extraction + user-supplied record → exactly ONE row per
  governing rule
- Multi-event extraction, extracted anchor only → same, ONE row per rule
- Two events yielding different dates under one rule → escalation, not two
  rows

## Verification
cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 333/1 — must not drop. GREEN or STOP.
