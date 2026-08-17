# LegalClear — What Happened Tonight, Explained in Plain English

This report explains everything done on the LegalClear remediation night run
(2026-08-16/17). It is written so that anyone — including a fresh Claude
session — can understand what happened, why, and what is left. No prior
context needed.

---

## 1. The setting

LegalClear went through a security/correctness audit (code `0c2e006`). The
audit produced findings, grouped into remediation phases A through H.
Earlier phases A and B1–B4 were done before tonight. Tonight's job was:

- Finish Phase B (the service-date correctness work, items B5-b through B5-f4)
- Run the "night run": finish Phases C, D, and E work in parallel lanes
- Close Phase F (the migration hole, gate G3) by getting a real CI migration
  system live

---

## 2. The star of the night: the "service date" bug (B5)

### 2.1 What the feature does

When a user uploads a court document, LegalClear reads it, figures out legal
deadlines, and shows them. For eviction cases, the most important date is
"when were you served" — that date starts the clock on the 5-business-day
answer deadline.

Sometimes the document doesn't say when the user was served, or the user
knows better than the document. So there is a feature: the user can TELL the
system "I was personally served on August 10" (or "it was posted on my door
on August 10, and the clerk mailed me a copy on August 12"). The system
should then compute the deadline from the user's answer.

### 2.2 The bug — one disease, four symptoms

The user's answer kept losing to the machine's own guess. We fixed it four
times, and each time a different symptom appeared:

1. **The date was ignored** — the machine used its extracted date instead of
   the user's date.
2. **Ordering** — the code checked "is the user's date allowed here?" BEFORE
   it ever read the user's date, so the user's date never had a chance.
3. **The method was ignored** — the date won, but HOW the user was served
   (personal vs posted) was forgotten, so "posted" cases computed the wrong
   kind of deadline.
4. **Clobbering** — the user's answers were stored as columns on the same
   database rows the pipeline rewrites every time it runs. Every recompute
   wiped the user's answers before reading them.

### 2.3 The real fix (B5-f3 + B5-f4)

The structural fix: **user-owned facts must never share a row with
machine-owned facts.** We created a separate table (`document_service_facts`)
that the automated pipeline NEVER writes. The user's answer lives there,
untouched. When deadlines compute, the system reads that row once, as a
unit, and its values override everything the machine extracted.

Then the final symptom appeared: duplicate deadline rows (two identical
cards). The document's text produced multiple extracted events, and the
user's answer got applied to each event. Fix (B5-f4): **one deadline per
legal obligation per document, unconditionally.** If two events would
produce two different dates for the same obligation, the system escalates
for review instead of showing two rows.

### 2.4 How we proved it (the live 4-case gate)

Unit tests kept passing while the live system stayed broken (the tests use
fake databases; the bugs were about ordering and state). So the real proof
is a live test against production with a real document:

| Case | Input | Expected | Result |
|---|---|---|---|
| 1 | personally served 08-10 | deadline from 08-10 | ✓ due 08-17, exactly one row |
| 2 | posted, but no mailing date given | reject with 422 error | ✓ 422 |
| 3 | posted 08-10, clerk mailed 08-12 | deadline from the LATER of the two (08-12) | ✓ due 08-19, one row |
| 4 | user doesn't know | escalate to human review, no deadline | ✓ escalated, zero rows, guidance shown |

This gate caught all four bug variants. It is the single most valuable test
in the project and gets re-run after every change to the deadline code.

One memorable detour: after the third fix, the live test STILL failed. Code
reading found nothing wrong. The real cause was in the service logs: the
production LLM API key had run out of credits ("credit balance too low"),
so every recompute silently used a degraded path. Topping up the account
fixed it. Lesson: when live behavior contradicts correct code, check the
service logs before re-reading code.

---

## 3. The parallel lanes (night run)

While the B5 work proceeded, other audit findings were fixed in parallel
"lanes" — separate git worktrees, each with one agent run, capped at 3
running at once, $40 total budget (about $19 was spent).

| Lane | What it did |
|---|---|
| Lane B | Added the attorney-referral tile to the HomeHub home screen; fixed the token-estimate counter on file upload |
| Lane D | Retired the DeepSeek model (repointed three code paths to Claude Haiku — one provider, one security story); put API-key protection on the attorney-referral intake; migrated the referral frontend to the shared API client; authored the RLS (row-level security) migration for the referral tables |
| Lane A | Built the user-facing service-date form (date + method + "I don't know" option), the recompute-on-edit behavior, and the friendly empty state for legacy documents with no stored text. Three branches edited the same file — the merge was a careful three-way union. |
| C2 | Email delivery adapter: reminders now go through a provider-agnostic adapter. It ships "dark" — no email API key exists yet, so reminders fail honestly instead of pretending. |

All lanes merged to main in order (B → D → A → C2), each with the full test
suite green (352 passed, 1 skipped at the end) and both services redeployed
and verified online.

---

## 4. Phase F: the migration system (the "what was skipped" part)

### 4.1 What a migration is

A migration is a small SQL file that changes the database's structure —
create a table, add a column, change a security policy. The repo has 31 of
them, each named with a timestamp, e.g. `20260813000000_add_users_and_referrals.sql`.

### 4.2 The problem

Until tonight, migrations were applied by hand: Joe pasted SQL into the
Supabase editor. That is error-prone and unrepeatable — the audit called it
"the migration hole" (gate G3).

### 4.3 The fix

A GitHub Actions workflow now applies migrations automatically. Key design:

- It uses the Supabase **Management API** with a personal access token
  (secrets in GitHub: SUPABASE_ACCESS_TOKEN + SUPABASE_PROJECT_REF). No
  database password exists anywhere.
- It applies files in **timestamp order**, strictly one at a time. Any
  failure halts immediately, prints the failing file and the database's
  error, and fails the job. No retries, no guessing.
- It keeps a **bookkeeping table** called `schema_migrations` that records
  every file it has applied. Before applying a file it asks "have I done
  this one before?" — if yes, it skips.

### 4.4 Why 26 files were "skipped" (your question)

The database was built BEFORE this system existed — 26 migration files were
applied by hand over the past months. If the new system re-applied them,
most would error out (tables already exist). So the first migration the new
system ran did two things:

1. Created the bookkeeping table.
2. Wrote the 26 old files' names into it, marked as "already applied."

From then on, when the workflow sees those 26 names, it skips them — not
because anything failed, but because **they are already part of the live
database and must never run again.** This is correct and desired: each
migration runs exactly once, ever.

The first CI run therefore:
- created the bookkeeping table
- skipped the 26 already-applied files
- actually applied 4 files that were new and had never run anywhere:
  1. `20260813000000` — the attorney-referral tables (they genuinely
     didn't exist in production — the run created them)
  2. `20260816000000` — F4 schema declarations (no-ops, tables exist)
  3. `20260816010000` — D2 RLS security on the referral tables
  4. `20260816020000` — C-2 cron job amendments

A final check (`parity_check.py`) compared every table and column in the
repo's migrations against the live database: **zero differences.** That
closed gate G3 — the migration hole is closed. Future pushes that add a new
migration file will trigger the workflow, which applies just the new file
and records it.

### 4.5 The debugging journey to get there (short version)

The first five attempts failed, each with a different, educational error:

1. 401 "Format is Authorization: Bearer ***" — the GitHub secret held
   something that wasn't a valid token.
2. 401 "JWT could not be decoded" — it held a project key (anon/service_role).
   The Management API needs a personal access token (`sbp_...`).
3. 404 "Cannot POST /v1/projects//database/query" — the project-ref secret
   was missing entirely (empty URL).
4. 400 "relation court_forms already exists" — an old migration re-ran
   (the skip list wasn't working yet).
5. "column ... does not exist" — a quoting bug: the workflow's JSON tool
   emitted double quotes, which SQL reads as column names, not text values.
   Fixed with single-quote SQL literals.

Each failure was honest, halted the run, and printed its error — exactly
the behavior the system is supposed to have.

---

## 5. Credentials summary (what exists where)

- **GitHub repo secrets (joewpb/legalclear):** SUPABASE_ACCESS_TOKEN
  (Supabase personal access token, `sbp_` format) and SUPABASE_PROJECT_REF
  (the project reference `miedifclpqewnixxkahs`). Used only by the migration
  workflow.
- **Railway:** unchanged. Backend + frontend both deploy from main.
- **Supabase app_config:** two new rows exist — `backend_url` and `api_key`
  — currently EMPTY placeholders. Joe must fill them with real values before
  the scheduled cron jobs (form change-detection, statute refresh,
  deadline reminders) can actually reach the backend. This is deliberate:
  deployment-specific values are never committed to the repo.
- **One password was shared in chat during the night and should be rotated**
  (the Supabase dashboard login). It is not stored anywhere by the agent.

---

## 6. Final state

| Thing | State |
|---|---|
| Phases A–F | Complete |
| Gates G1–G5 | Closed |
| Test suite | 352 passed, 1 skipped |
| Live 4-case gate | All four pass |
| Migration pipeline | Live, auto-triggered, tracking works |
| Schema parity | Zero drift |
| Both services | Online |
| Budget | ~$19 of $40 spent |

### Still open (deliberately)

1. **Decision 6 attorney confirmation** — the "posted service = later of
   posting and clerk mailing" rule (Florida § 48.183) needs a Florida
   attorney to confirm it before the feature is publicly announced. Until
   then G1 stays formally closed.
2. **C2 email** — the adapter is built but no email API key exists. Choose
   a provider (Resend was recommended) and add the key; until then,
   reminders fail honestly.
3. **Phase G** — cleanup (delete deprecated columns, old tables, dead
   code). Requires Joe's explicit word.
4. **Phase H** — rebuilding documents; nothing dispatched yet.

---

*This report was written by the LegalClear orchestration agent after the
night run. Raw evidence lives in the repo's git history on main
(origin/main = 1744989), the run logs under runs/, and REMEDIATION_PLAN.md.*
