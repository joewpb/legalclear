# Dispatch G1-1 — backend anchor date + provenance on deadline rows

Repo: joewpb/legalclear. Worktree: ~/code/lc-g11 (branch fix/g11-anchor-provenance, cut from origin/main).

## Task

GET /api/deadline/{id}/deadlines must expose, for EVERY deadline row, the anchor
date the computation ran from and where it came from (user_supplied vs
extracted). This powers the educational-framing standard (AGENTS.md principle
2b, condition 2) — the frontend slice consumes it next.

1. Read backend/src/api/routers/deadline.py end to end: the GET /deadlines
   handler, its _SELECT_COLUMNS, the Pydantic response models, and how rows map
   to ComputedDeadline. Read backend/src/memory/db.py for the deadlines and
   trigger_events table access. The anchor data lives in trigger_events
   (event_date = the extracted/service anchor; service_date_provenance =
   'user_supplied' | 'extracted') and document_service_facts (user-supplied
   service record, B5-f3). Each deadlines row is tied to a trigger event — find
   the join key (trigger_event_id or document_id) and use it.
2. Add two fields to every deadline row in the response:
   - `anchor_date` — the date the computation used as its trigger/start.
   - `anchor_provenance` — "user_supplied" if the anchor came from the user's
     service-date submission (document_service_facts / service_date_provenance
     = user_supplied), else "extracted" (from the document). For posted
     service, the anchor is the later-of effective date — provenance should
     reflect that the posting date was user_supplied and the mailing date
     extracted-from-docket; express both as `anchor_date` (effective) and keep
     the provenance as the combined truth: "user_supplied" when either input
     was user-supplied, with a short `anchor_note` if warranted (your call —
     keep it simple and honest).
3. Update the Pydantic response schema + the SQL/PostgREST SELECT so the fields
   actually serialize (they must appear in the API response, not just the DB).
4. Tests: extend the router-layer tests (backend/tests/test_deadline_service_date.py
   or a new test_g11_anchor_provenance.py — pure-Python, monkeypatched DB like
   the existing router tests): personal service with user-supplied date →
   anchor_date + provenance "user_supplied"; extracted-only path → "extracted".
   Do NOT hit live services.

## Verify

Run the suite with the CI-scope ignores from .github/workflows/pytest.yml
(baseline 369 passed, 1 skipped). Zero NEW failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network (no
curl, WebFetch). No railway/supabase. Edit in place — orchestrator commits.
Do not touch frontend. Final answer: fields added with file:line, the join
used, test results, any edge cases, turn count.
