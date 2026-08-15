# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S3-3 (AUDIT_FINDINGS.md §6):
"No startup config validation anywhere — `config.py`. Missing SUPABASE/ANTHROPIC creds →
degraded-mode empty product (20 guard sites) instead of a crash; Joe's stated rule:
'config that is missing must raise loudly.' Proposed fix: startup validator — required
vars fatal outside `ENVIRONMENT=development`. Blast radius: local dev ergonomics;
degraded-mode tests. Indep: yes."

DECISIONS.md Group B: S3-3 (startup config validation).

## Context and standing doctrines
- DECISIONS.md standing rule: "Config that is missing must raise loudly at startup,
  never degrade to empty." Never a default secret.
- A prior fix (S1-1, branch fix/s1-1-apikey-failfast, NOT merged) already made missing
  API_KEY raise at module import. Read `backend/src/core/config.py` as it exists on this
  branch to avoid duplicating or conflicting with that; this item is about the OTHER
  required credentials (Supabase, Anthropic) and whatever else config.py reads.
- CRITICAL pitfall (learned in S1-1): a module-import fail-fast breaks pytest collection
  in CI, where no .env and no secrets exist. Simulate CI exactly when verifying: run the
  import and the CI-scope suite from a cwd with no .env file, with only the env vars CI
  would have. If your mechanism breaks CI collection, either (a) validate at FastAPI
  app startup instead of import (preferred — tests import modules, only the server
  startup enforces), or (b) add dummy env vars to the pytest job in
  `.github/workflows/pytest.yml` using the same pattern as the existing `API_KEY:
  ci-test-key` entry on the test step. Pick whichever keeps CI green and prod
  fail-loud.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Done means
1. A test that fails before and passes after. Show both runs.
2. Minimal diff.
3. Full suite green (CI-scope command, exact):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py
4. One paragraph: what was wrong, what changed, what could regress.
