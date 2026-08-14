# TASK: Read-only reconnaissance. Change no code. Do not write any file.

This repo was audited at commit 0c2e006. AUDIT_FINDINGS.md and DECISIONS.md exist at the
repo root — consult only the sections relevant to the two questions below (see audit
§4.6, §4.8, §7 Q1/Q2, and DECISIONS "Blocked items").

## Question 1 — Migration mechanism
What mechanism is believed to apply `supabase/migrations/*.sql` to the production
Supabase database? Gather evidence with file:line references:

- `backend/railway.json` — what does it declare (build/start/cron)?
- `.github/workflows/*.yml` — is there any job that touches supabase, runs migrations,
  or deploys to Railway? Which workflows exist and what do they actually do?
- `deploy/` directory — full contents summary.
- `backend/migrations/` vs `supabase/migrations/` — are there TWO migration mechanisms?
  Which one does code/docs treat as authoritative? Do the two dirs overlap or diverge?
- Docs mentioning how migrations reach prod: CLAUDE.md, AGENTS.md, README.md, docs/,
  SPEC_LEDGER.md, INTEGRATION_PLAN.md, STATUS.md, phases/*.
- Migration file naming pattern (supabase-CLI-style timestamps?) and any
  supabase/config.toml or CLI hints anywhere in the repo.

Verified input from the audit (do not re-litigate): as of 2026-08-13, production applied
migration 20260812 (citation_treatment) but NOT 20260704 (filings), 20260808 (closures
seed), or 20260813 (users/referrals). Use that asymmetry as a clue: what process could
apply SOME files but not others?

Conclusion required: name the mechanism (or "no mechanism exists in-repo"), with
confidence: VERIFIED / INFERRED / UNKNOWN. List every migration file whose application
status can be inferred from repo evidence only.

## Question 2 — Railway evidence (repo-side only)
You CANNOT read Railway directly: no railway CLI exists on this machine, no credentials
are available, and you must not attempt any network access. Determine the strongest
repo-side evidence for each of these environment variables in the Railway service
("zesty-delight"): what the code reads, what `.env.example` documents, whether
`backend/railway.json` or any workflow references it, and whether CI would set it.

Variables: API_KEY, PAYMENTS_ENABLED, DEEPSEEK_API_KEY.

For each, output exactly one status word: VERIFIED (value known from repo evidence),
INFERRED (name documented somewhere with a value or explicit setting), or UNVERIFIED
(needs Railway dashboard access). Never invent values. Note the exact config.py lines
where each is read, and what the code does when each is unset.

## Local tooling
Report whether these exist on this machine and, if present, what they are linked to:
railway CLI, supabase CLI, psql, any ~/.railway* files, any RAILWAY_* env vars set.

## Output
A single markdown report in your final response:
1. MIGRATION MECHANISM — evidence bullets with file:line, then conclusion + confidence
2. RAILWAY EVIDENCE — table: variable | where read (file:line) | .env.example value | status
3. LOCAL TOOLING — present/absent per tool
4. UNVERIFIED — everything that requires Railway dashboard or Supabase access

Be explicit about verified versus inferred on every line. Investigation only. No code
changes, no file writes.
