# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the section for this item — do not read either file
end to end.

## The defect
Triage S1-3 (AUDIT_FINDINGS.md §6):
"Unauthenticated PII read + unauthenticated upsert-by-email — `attorney_referral.py:88-135`.
Any UUID → full profile; any email → overwrite profile. Proposed fix: require auth or at
minimum a per-session token; never upsert on client-supplied email without verification.
Blast radius: attorney-referral frontend flow."

Approved decision (DECISIONS.md, Group A item 4 / not-blocked list):
"S1-3 attorney-referral endpoint auth (code-only; tables need not exist to add auth)."

## Scope resolution (authoritative for this run)
- The repo has exactly one auth pattern: the API-key dependency (see how other key-gated
  routers use `require_api_key` / `verify_api_key` from core). No per-session-token
  infrastructure exists anywhere. So the fix is: apply the repo's standard auth
  dependency + rate limit to the attorney-referral routes, mirroring how the other
  protected routers are written. Do NOT invent a session-token system.
- The upsert-on-client-supplied-email hardening (verification step) is OUT OF SCOPE for
  this run: one line in FOLLOW_UPS.md, then move on.
- Routes in scope: everything registered in `backend/src/api/routers/attorney_referral.py`
  (`POST /api/attorney-referral/users`, `GET .../users/{user_id}`, intake, submit, and any
  others present). Read the file first and enumerate its routes.
- Do not change the frontend in this run unless a route's response shape would break the
  shipped caller — if the frontend would break, STOP and report instead of coding.

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
