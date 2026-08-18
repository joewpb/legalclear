# VERIFY.md — mechanical verification of the documentation ledger

**Added 2026-08-17 (Phase H).** `SPEC_LEDGER.md` makes concrete, checkable claims:
every capability row names a code path and a test path, and the absence sections
claim specific files are gone. This page describes the tool that proves those
claims against the tree, so the ledger cannot silently rot the way the pre-Phase-H
documents did (audit finding 7).

## How to run

```bash
make verify-docs
# equivalently:
python3 scripts/verify_docs.py
```

No network, no pytest, no dependencies beyond the Python 3 standard library.
Exit code 0 = every claim holds; non-zero = at least one claim is false.

## What it checks

1. **Ledger paths exist.** Every backticked file path in the *code path* and
   *test path* columns of the capability ledger table in `SPEC_LEDGER.md` must
   exist as a file in the repo. One PASS/FAIL line per path.
2. **Phase G absences hold.** The files Phase G deleted (analysis router, the
   five dead frontend components) must NOT exist.
3. **Grep-level claims.** The ledger carries the last-verified SHA (`f145dd8`)
   and date (`2026-08-17`); `backend/src/api/routes.py` contains no push-token
   surface, no top-level `/eligibility`, and no analysis-router registration;
   the triage router is still marked AMBIGUOUS; `docs/ADRS.md` contains the
   verbatim case-law ADR.

The run ends with a `SUMMARY: N/N checks passed` line.

## When it must be run

- In the same commit as **any** edit to `SPEC_LEDGER.md` (per the ledger's change
  protocol).
- After any file move/delete that could invalidate a ledger row — if it fails,
  fix the ledger row (or the tree), never the verifier.

## What it deliberately does not do

- It does not prove a capability *works* — that is the test suite's job
  (`cd backend && uv run pytest tests/` with the CI ignore list in
  `.github/workflows/pytest.yml`; baseline at f145dd8: 352 passed, 1 skipped).
- It does not touch the network, the database, or deployed services.
