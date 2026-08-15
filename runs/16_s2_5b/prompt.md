# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). A supervised prod smoke test on 2026-08-14 found this live defect. Fix only
the named defect.

## The defect (S2-5b — found live in prod)
`backend/src/api/routes.py:333` calls `explainer.explain(doc, classification, lang)` —
4 positional args — but `ExplainerAgent.explain()` (`backend/src/agents/explainer.py:46`)
has signature `async def explain(self, text: str, language: str = "en") -> dict`.
Prod /process 500s deterministically: "TypeError: ExplainerAgent.explain() takes from 2
to 3 positional arguments but 4 were given" (verified live on two documents).
Compare: `explain_stream(self, text: str, language: str = "en")` at explainer.py:67 —
the refactor tightened the API to (text, language) and the /process call site was not
updated.

## Scope resolution (authoritative for this run)
- Read the /process handler (routes.py ~310-380), ExplainerAgent.explain, and every
  other caller of `explain(` in backend/src (there may be more stale call sites — fix
  only ones that pass the old wrong arity; log any others).
- Fix the call site(s) to match the current signature. The handler has the raw
  `document_text` string in hand (`doc_record["document_text"]`) — that is what
  `text` should receive. If `classification` context is needed by the explainer, the
  current signature does not accept it — do NOT widen the signature; pass text and
  language only.
- CHECK the same `asyncio.gather` block: `risk_scanner.scan(doc, classification, lang)`
  — verify `scan()`'s current signature and fix identically if it was hit by the same
  refactor. If scan is broken too, it fails right after explain — fix both in this run
  (they are the same defect: stale /process call sites).
- Do not touch the upload handler's text-key bug (separate run S2-5a).
- Backend only.

## Standing doctrines
- No LLM in date arithmetic; deterministic code computes.
- uv for Python. No pip, no poetry.

## Done means
1. A test that fails before and passes after. Show both runs. (Check existing
   backend/tests for /process or agent tests and reuse their mock pattern; the test
   must prove the handler now calls explain/scan with the correct arguments — e.g.,
   mocked agents capturing call args.)
2. Minimal diff.
3. Full suite green (CI-scope command, exact):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py
4. One paragraph: what was wrong, what changed, what could regress.
