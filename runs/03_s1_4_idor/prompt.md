# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the section for this item — do not read either file
end to end.

## The defect
Triage S1-4 (AUDIT_FINDINGS.md §6):
"IDOR: deadline GETs (no auth at all); `/document`, `/documents/{user_id}`, `/chat/{id}`
(shared key, no ownership) — `deadline.py:43,62`; `routes.py:389-419`. Anyone (or any key
holder) reads any user's legal situation. Proposed fix: session-scope like
`delete_document` (`routes.py:227`) already does. Blast radius: ResultsPage must pass
session identity."

Approved decision (DECISIONS.md, Group A item 3) — THIS SCOPES THE ITEM:
"S1-4 IDOR on deadline GETs (`routers/deadline.py:43,62`) — scope to the owning user."

So: fix `backend/src/api/routers/deadline.py` GETs only. The `routes.py:389-419`
(document/chat IDOR) is a separate later item — put ONE line in FOLLOW_UPS.md, then move
on. Do not touch routes.py.

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
