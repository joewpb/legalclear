# TASK: C-1 — author CI migration workflow + parity job + F4 backfill migrations. DO NOT ENABLE.

Repo: root. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-c, branch fix/c1-ci-migrations (checked out).

## Job 1 — CI migration workflow (AUTHOR, DO NOT ENABLE)
.github/workflows/migrate.yml — workflow_dispatch AND push trigger
COMMENTED OUT (a YAML comment on the `on:` push key or equivalent so it never
auto-fires until the orchestrator uncomments it at Lane-C fan-in):
- Applies supabase/migrations/*.sql in timestamp order (the files are named
  YYYYMMDDHHMMSS_*.sql — sort lexically) via psql with ON_ERROR_STOP=1.
- Credential from GitHub secret SUPABASE_DB_URL (a postgres connection URL).
- Postgres client via a GitHub-hosted runner (ubuntu-latest), install
  postgresql-client, run: for f in $(ls supabase/migrations/*.sql | sort);
  do psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$f"; done

## Job 2 — parity job wiring
.github/workflows/parity.yml — a job that runs scripts/parity_check.py
(it exists) and fails the build on drift (nonzero exit). Plain python run.

## Job 3 — F4 backfill migrations (author only, do not apply)
Read the prod schema READ-ONLY (never write) and author idempotent backfill
migrations in supabase/migrations/ (NEW files, timestamped LATER than
20260815000002 so CI ordering is sane) declaring the current state of:
legal_opinions, court_forms, usage_stats, users — as CREATE TABLE IF NOT
EXISTS ... matching the prod column sets, with RLS enabled, plus indexes that
exist in prod. How to read prod schema without credentials: use the repo's own
existing migration files (supabase/migrations/*) as the schema source of
truth, and cross-check anything uncertain via grep. Do NOT invent columns —
if a table's definition isn't discoverable from repo artifacts, write the
migration with a TODO comment and say so in your report.

## Rules
No CI triggers enabled. No prod writes. No secrets printed. Report: workflow
file:lines, parity wiring, each backfill migration file + its column sources,
and whether any table was undiscoverable.
