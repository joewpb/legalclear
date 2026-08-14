# TASK: Complete the S1-4 fix already in progress. Do exactly this and nothing else.

This repo was audited at 0c2e006. A prior run on branch `fix/s1-4-deadline-idor` ran out
of turns mid-fix. The working tree already contains:

1. `frontend/src/pages/ResultsPage.jsx` — MODIFIED: `fetchDeadlines(documentId,
   sessionId)` now passes `session_id` as a query param to
   `GET /api/deadline/{document_id}/deadlines` (and the sibling trigger-events fetch, if
   it calls the API the same way — check it).
2. `backend/tests/test_deadline_router_idor.py` — NEW test file defining the expected
   contract (fakes the DB; expects 404 for wrong session, 200 with the existing response
   envelope for the owning session).

Your job — the backend half only:

- Read `backend/src/api/routers/deadline.py` (handlers at lines 43 and 62) and the
  positive control pattern in `backend/src/api/routes.py:227-238` (`delete_document`
  checks the document's `session_id` against the caller before acting).
- Implement the same ownership check in BOTH deadline GET handlers: read `session_id`
  from the query params; load the document (`db.get_document(document_id)` or whatever
  the module already uses); if the document is missing OR its `session_id` does not match
  the caller-supplied `session_id`, return 404 (same shape/status the handlers already
  use for not-found). A missing `session_id` param must also be rejected (404).
- Do NOT change the public response shape of the success path. If the existing test
  file's success assertion disagrees with the handler's current envelope, adjust the TEST
  to match the handler — never the other way around.
- Run the new tests BEFORE any code change and show the failure (wrong-session request
  currently returns 200 — that is the failing-before evidence). Then make the minimal
  diff. Then run the new tests again (green), then the full CI-scope suite:
  `uv run pytest tests/ -q --ignore=tests/test_full_v1.py --ignore=tests/test_phase_2.py
  --ignore=tests/test_phase_16.py --ignore=tests/test_phase_17.py
  --ignore=tests/test_phase_18.py --ignore=tests/test_phase_20.py
  --ignore=tests/test_phase_21.py --ignore=tests/test_phase_22.py
  --ignore=tests/test_phase_23.py --ignore=tests/test_pc_integration.py`
  (expect ~199 passed + the new ones; server-dependent excluded files may fail — that is
  expected and not your problem).
- The frontend change is already made; leave it alone unless you find a concrete bug in
  how it passes session_id (e.g. the trigger-events call missing the param) — fix only
  that call if so.

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
1. Show the new tests failing before and passing after.
2. Minimal diff.
3. Full suite green.
4. One paragraph: what was wrong, what changed, what could regress.
