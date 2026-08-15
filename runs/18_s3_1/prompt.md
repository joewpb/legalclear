# TASK: Build the schema-parity check (S3-1). One deliverable, no prod writes.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md S3-1: prod schema vs
supabase/migrations parity is UNKNOWN — "the exact migration list that is applied in
prod is unknown." DECISIONS.md: a parity check is the prerequisite before any further
migration application. The migration-mechanism question is now settled: there is NO
automated mechanism — migrations have been applied manually and partially. This run
builds the CHECK.

## Verified prod facts (2026-08-14, read-only REST probe — use these in your docs/report,
## do not re-verify by network)
Tables present in prod (HTTP 200): chat_messages, citation_treatment, court_closures,
court_forms, court_rules, deadline_reminders, deadlines, documents, legal_opinions,
local_administrative_orders, packets, push_tokens, sessions, statutes, trigger_events,
usage_stats, users.
Tables MISSING in prod (404): attorney_inquiries, user_profiles, filings.
(court_closures now has 108 rows — statewide + local seeds both applied.)
The prod Supabase project is miedifclpqewnixxkahs; the REST endpoint is
https://miedifclpqewnixxkahs.supabase.co/rest/v1/ with apikey + Bearer service key.

## Deliverable
A script in the repo (suggest scripts/parity_check.py; follow existing scripts/
conventions) that:
1. Enumerates every CREATE TABLE in supabase/migrations/*.sql (table name + column
   names + types), parsing the SQL reliably (plain-text parse of the create-table
   stanzas is fine — document its limits).
2. Probes the prod schema read-only. Two options, use BOTH where cheap:
   a. The PostgREST OpenAPI document at GET /rest/v1/ with Accept:
      application/openapi+json (it lists exposed tables + columns), and
   b. Per-table REST probe with select=*&limit=1 (200/404 + column keys).
3. Outputs a parity report: missing tables, extra prod tables, column-level diffs
   per table, plus a machine-readable summary (JSON) for CI.
4. Env contract: reads SUPABASE_URL and SUPABASE_SERVICE_KEY from environment or the
   existing backend/.env loader — NEVER prints or logs the key.
5. Usage instructions in the script docstring (uv run python scripts/parity_check.py).

## Tests
The script must be testable offline: a test (backend/tests/test_parity_check.py or
scripts/test_parity_check.py matching repo layout) that feeds it a fixture of migration
SQL + a fake probe response and asserts the diff output (missing table detected, extra
table detected, column diff detected). Show red→green. No network in tests.

## Rules
- uv for Python. No pip, no poetry.
- No changes to any migration file. No prod writes of any kind.
- Do not commit any key or secret.
- Full suite green (CI-scope command, exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
  (plus any new test file paths)
- Report: file layout, how it works, test evidence, parity-report sample against the
  prod facts above (run the script if you can with the repo's own .env — do not print
  the key).
