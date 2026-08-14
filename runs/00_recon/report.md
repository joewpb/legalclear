## MIGRATION MECHANISM

**Evidence:**

- `backend/railway.json:1-11` — declares only `build.builder: NIXPACKS` and `deploy.startCommand/healthcheckPath/restartPolicy`. **No migration step, no pre-deploy hook, no cron block.** Railway is not told to run any SQL.
- `.github/workflows/` contains exactly 4 files: `node.js.yml`, `pytest.yml`, `eval-deadline.yml`, `gitleaks.yml`. Read all four in full:
  - `node.js.yml:1-38` — `npm ci` / `npm run build` / `npm test` in `frontend/`. No Supabase, no Railway CLI, no deploy step.
  - `pytest.yml:1-61` — `uv sync` + `uv run pytest tests/` with several integration test files ignored. No Supabase reference.
  - `eval-deadline.yml:1-41` — `uv run python -m evals.run_all` (fast mode, no LLM). No Supabase reference.
  - `gitleaks.yml:1-23` — `gitleaks/gitleaks-action@v2` secret scan only.
  - **None of the four workflows contain the string "supabase", "migration", "railway", or any deploy/push step.** CI builds and tests; it does not ship anything anywhere.
- `deploy/` (3 files) — `legalclear-backend.service`, `legalclear-frontend.service`, `nginx.conf`. All three reference `WorkingDirectory=/home/joe/.gemini/antigravity/scratch/legalclear/...` — a path outside this repo, from an unrelated local scratch checkout. This directory is **not connected to Railway or Supabase in any way**; it looks like a stale/foreign local-systemd artifact, not deploy tooling for this project.
- `supabase/migrations/*.sql` (22 files) vs `backend/migrations/2026_05_15_packets.sql` (1 file) — **two migration directories exist.** `backend/migrations/` has a single May-2026 file that predates the `supabase/migrations/` convention (which starts at `20260519190000`) and appears to be a superseded/orphaned leftover — nothing in CLAUDE.md, SPEC_LEDGER.md, or any workflow references `backend/migrations/`. CLAUDE.md's "Database (Supabase)" section names only `supabase/migrations/` as canonical. The two dirs do not overlap in filenames or numbering scheme; `backend/migrations/` is dead weight, not a competing live mechanism.
- No `supabase/config.toml` exists anywhere in the repo (`find . -iname config.toml` returned nothing) — i.e., there is no Supabase CLI project link committed, and migration filenames (`20260519190000_...`, `20260812000000_...`) follow the Supabase-CLI timestamp convention but that alone doesn't imply the CLI is actually invoked anywhere in this repo's automation.
- CLAUDE.md: "Migrations live in `supabase/migrations/`. Never run migrations directly against production without first verifying on a Supabase development branch. Additive-only changes... can go direct; any DDL that drops or restructures must go through a branch." This describes a **human/manual workflow policy**, not an automated mechanism — it never says CI or Railway applies migrations.
- Memory record `project-supabase-branching-enabled.md` (this session's index) claims "migrations auto-apply to prod on merge to main" — but no artifact in this repo (no workflow, no Railway config, no GitHub App config file) implements or confirms that. This appears to be an unverified belief, not evidence.
- AUDIT_FINDINGS.md §4.8/§7 independently reached the same conclusion: prod has `citation_treatment` (20260812) but not `20260704`, `20260808`, or `20260813` — an inconsistent/partial application pattern inconsistent with any single deterministic mechanism (a real CI-driven or Supabase-branch-merge mechanism would apply all committed migrations in order, or none).

**Conclusion:** No in-repo mechanism applies `supabase/migrations/*.sql` to production. The most plausible explanation for the asymmetry (20260812 applied, 20260704/20260808/20260813 not) is **manual, ad-hoc application** — e.g., someone ran a single migration by hand (SQL editor, Supabase dashboard, or `supabase db push` from a local machine) at some point, and the rest were simply never applied. There may be a Supabase-native "auto-apply on branch merge" feature configured entirely in the Supabase dashboard (invisible to this repo), but if so it isn't functioning consistently, since sequential migrations after 20260704 were skipped while a later one (20260812) landed.

**Confidence: VERIFIED** that no repo-based mechanism (CI, Railway build/deploy hook, checked-in CLI config) exists. **INFERRED** that application is manual/ad-hoc, based on the partial-application pattern. **UNKNOWN** whether a Supabase-dashboard-configured auto-merge integration exists outside repo visibility — that requires Supabase dashboard access to confirm or rule out.

**Migration files whose prod-application status is knowable from repo evidence + the audit's DB probes (not re-derived by me, per instructions — cited from AUDIT_FINDINGS.md §4.8):**
| Migration | Status |
|---|---|
| `20260812000000_add_citation_treatment.sql` | Applied (table exists, 0 rows) |
| `20260704000000_add_filings_table.sql` | Not applied (404) |
| `20260808000000_seed_local_court_closures.sql` | Not applied (only 9 May-seeded rows present) |
| `20260813000000_add_users_and_referrals.sql` | Not applied (404) |
| All earlier files (≤ `20260723120000`) | Presumed applied — base schema, forms, law tables etc. are confirmed live per audit §4/§7 tables (not independently re-verified by me here) |

## RAILWAY EVIDENCE

| Variable | Where read (file:line) | `.env.example` value | Status |
|---|---|---|---|
| `API_KEY` | `backend/src/core/config.py:29` — `os.getenv("API_KEY", "testkey123")` | `backend/.env.example:13` → `API_KEY=` (blank placeholder) | **UNVERIFIED** — code default is the known string `"testkey123"` if unset (that default value is VERIFIED from source), but whether Railway's actual env var is set to something else is not knowable from the repo. |
| `PAYMENTS_ENABLED` | `backend/src/core/config.py:37-38` — `os.getenv("PAYMENTS_ENABLED", "false").lower() in ("true","1","yes","on")` | `backend/.env.example:18` → `PAYMENTS_ENABLED=false` | **UNVERIFIED** — code defaults to `False` (payments off) if unset; actual Railway value not knowable from repo. |
| `DEEPSEEK_API_KEY` | `backend/src/core/config.py:30` — `os.getenv("DEEPSEEK_API_KEY", "")` | **Not present in `backend/.env.example`** (confirmed absent — grep found zero matches) | **UNVERIFIED** — no default beyond empty string; not documented in `.env.example` at all (matches AUDIT_FINDINGS.md S4-7 "`.env.example` missing 5 vars code reads"). No workflow or `railway.json` reference. |

None of the three appear in `backend/railway.json` (which contains no `env` block) or in any `.github/workflows/*.yml` (none reference `API_KEY`, `PAYMENTS_ENABLED`, or `DEEPSEEK_API_KEY`, and CI never sets Railway env vars regardless). Code behavior when unset, verified from source:
- `API_KEY` unset → auth defaults to the shipped-with-source string `"testkey123"` (per AUDIT_FINDINGS.md §7 item 3, this is a live concern, not hypothetical).
- `PAYMENTS_ENABLED` unset → `False`, paywalls off.
- `DEEPSEEK_API_KEY` unset → empty string; any DeepSeek call-site would fail/no-op (not traced further here — out of scope of this recon).

## LOCAL TOOLING

| Tool | Status |
|---|---|
| `railway` CLI | **Absent** — not on `PATH` (`which railway` returned nothing) |
| `supabase` CLI | **Absent** — not on `PATH` |
| `psql` | **Absent** — not on `PATH` |
| `~/.railway*` files | Could not enumerate — home-directory listing outside `/home/joe/code/legalclear` is blocked by this session's sandbox (`ls` on `/home/joe` was refused: "may only list files in the allowed working directories"). **UNVERIFIED**, not confirmed absent. |
| `RAILWAY_*` env vars | **Absent** — `env | grep -i railway` returned nothing in this shell session. |

## UNVERIFIED (requires Railway dashboard / Supabase dashboard / broader filesystem access)

1. Actual current value of `API_KEY`, `PAYMENTS_ENABLED`, `DEEPSEEK_API_KEY` in the Railway `zesty-delight` service — dashboard access required.
2. Whether Supabase's dashboard has a native "auto-apply migrations on branch merge" integration configured outside this repo (would explain partial application if it exists but has been intermittently broken, disconnected, or manually overridden) — Supabase dashboard access required.
3. Whether `~/.railway/` or `~/.supabase/` config/credential files exist elsewhere on this machine outside the current session's allowed directory (`/home/joe/code/legalclear`) — session sandbox blocks this.
4. Whether `20260812000000_add_citation_treatment.sql` was applied via manual SQL-editor paste, a one-off local `supabase db push`, or some other out-of-band action — no artifact in the repo records how it landed.
5. How `legal_opinions` reached 425,850 rows (per AUDIT_FINDINGS.md §4.8/§7) — no ingestion script or migration in-repo accounts for it; this is a separate open question from the migration-apply mechanism itself.
