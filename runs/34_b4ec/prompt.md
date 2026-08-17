# TASK: B4e-c — Decision 5 check for forms.py (1 call site). Verify, then act minimally.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4e-c-forms-conditional (already checked out).

## Context
Decision 5 (DECISIONS.md): error with no prior substantive content → no disclaimer
needed; error AFTER substantive content → MUST carry the disclaimer. forms.py (B4b-3,
merged) emits typed `event: disclaimer` on its SUCCESS paths; its ERROR path
(forms.py:567-572 area) embeds the disclaimer as a FIELD inside the error_payload
dict on an untyped event — it does not emit a separate typed disclaimer frame.

## Job (1 call site — forms.py error path)
1. Inspect the error path with file:line evidence: does the error fire only after
   substantive content may have been emitted, only before, or both (multiple error
   exits)?
2. Apply Decision 5 exactly:
   - Error exits that can occur AFTER substantive content → the embedded disclaimer
     field in the error payload satisfies "carries the disclaimer" (keep it), AND if
     any such exit lacks it, add it. A separate typed frame is NOT required here —
     the embedded field already reaches the client. State this reasoning in the report.
   - Error exits that occur BEFORE any content → per Decision 5 they need nothing;
     if they currently embed the disclaimer, that is harmless over-emission — leave
     it unless removing it simplifies (do NOT churn code for cosmetics).
3. Tests: pin the current (verified) behavior per exit — for each error exit assert
   the disclaimer field presence/absence matches the Decision-5 truth for that exit.
   Extend backend/tests/test_forms_disclaimer_sse.py.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 275/1 — must not drop.

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: the error-exit inventory with file:line, what you changed (or why nothing
  needed changing), test evidence, suite count.
