# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the section for this item — do not read either file
end to end.

## The defect
Triage S1-1 (AUDIT_FINDINGS.md §6):
"`API_KEY` server default `"testkey123"` — `config.py:30`. If Railway env lacks `API_KEY`,
every 'protected' endpoint accepts a public string."

Approved decision (DECISIONS.md, Group A item 1):
"remove the default entirely; the app must refuse to start if `API_KEY` is unset. Never
degrade to a default secret."

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- No LLM in date arithmetic. No LLM call without explicit user action.
- Missing config raises loudly at startup — never degrades to [], None, {}, or a default.
  Never a default secret.
- uv for Python. No pip, no poetry.

## Done means
1. A test that fails before and passes after. Show both runs.
2. Minimal diff.
3. Full suite green.
4. One paragraph: what was wrong, what changed, what could regress.
