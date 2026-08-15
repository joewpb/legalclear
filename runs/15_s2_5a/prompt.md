# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). A supervised prod smoke test on 2026-08-14 found this live defect. Fix only
the named defect.

## The defect (S2-5a — found live in prod)
`backend/src/api/routes.py:294` stores `doc.get("text", "")` as the document text, but
`ingest_document()` (`backend/src/ingestion/__init__.py`) returns the extracted text
under the key **`cleaned_text`** (return dict keys: `error`, `raw_text`, `cleaned_text`,
`page_count`, `filename`, `ingestion_method`). There is no `"text"` key. Consequence:
every upload in prod stores an EMPTY `document_text` (verified: 0 non-empty rows across
47 documents), so the deadline pipeline 422s on "no extractable text" for every real
user. This is the root cause of the S2-5 "pipeline never ran" mystery.

## Scope resolution (authoritative for this run)
- Fix the key at routes.py:294: use `doc.get("cleaned_text", "")`.
- While touching that exact statement, check whether the same handler's
  `doc.get("token_estimate", 0)` also references a nonexistent key (it does — the
  ingestion return dict has no `token_estimate`). Do NOT fix it in this run; log it as
  a one-line FOLLOW_UPS.md entry (it only affects token-count bookkeeping, not text).
- Do not touch anything else in the upload handler, the ingestion module, or the
  explain/process flow. A separate run (S2-5b) fixes the /process signature bug — stay
  away from it.
- Backend only.

## Standing doctrines
- No LLM in date arithmetic; deterministic code computes.
- uv for Python. No pip, no poetry.
- Never store empty text when extraction succeeded.

## Done means
1. A test that fails before and passes after. Show both runs. The test must prove the
   upload path persists the extracted text — the cleanest approach: a focused unit test
   around the mapping (e.g., calling the upload handler with a mocked ingest_document
   returning the real key set and asserting create_document received the cleaned_text
   value), matching however the repo's existing upload tests are structured (check
   backend/tests first — reuse their mock pattern).
2. Minimal diff.
3. Full suite green (CI-scope command, exact):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py
4. One paragraph: what was wrong, what changed, what could regress.
