# S2-5 Diagnosis — why the deadline→reminder pipeline has never executed end to end

Run: `runs/13_s2_5_diagnose` · 2026-08-14 · Investigation only, no code changed.
Scope inputs: AUDIT_FINDINGS.md S2-5 row (line 314) + §4.8 (line 168); DECISIONS.md Group C (lines 84–89). Prod counts supplied by orchestrator (not re-verified; no network in this run).

## TL;DR verdict

The chain is **wired in code but broken in three independent places in production**, and one of them (the reminder half) was **never wired at all**:

1. **Upstream (documents → trigger_events/deadlines): the writer exists and is reachable, but only via a lazy, user-initiated frontend call that shipped 2026-06-09 — and every invocation either never happened or failed silently.** 0 rows across 45 documents means `/api/deadline/analyze` has never once succeeded in prod.
2. **Downstream (deadlines → reminders): structurally impossible.** The `deadline_reminders` table's migration never reached prod (table 404s), so the reminder processor cannot write even if called.
3. **The caller of the reminder processor (pg_cron → backend) was never configured.** The cron job is scheduled by the same unapplied migration, the GUCs it reads (`app.backend_url` / `app.api_key`) are set by **no migration in the repo**, and no migration enables the `pg_net` extension the job depends on. The `app_config` *table* in prod (which holds `backend_url`/`api_key`) is referenced by **nothing** in the repo — values were parked in a table no code reads.
4. **push_tokens has no reachable writer at all:** its only endpoint is meant for the React Native app, which is an empty directory.

The first break — the one that gates everything downstream — is that **`POST /api/deadline/analyze` has never successfully run**. Until a document produces `deadlines` rows, the reminder half (broken or not) has nothing to process.

---

## 1. The intended writers

### trigger_events — VERIFIED
- **Writer:** `backend/deadline/pipeline.py:242` — `db.client.table("trigger_events").insert(row)` inside `_write_trigger_event()` (`pipeline.py:219-246`), called from `run_deadline_pipeline()` at `pipeline.py:130,141,154,172` (once per extracted event, including escalated/failed-parse events "for audit purposes").
- **Trigger:** `POST /api/deadline/analyze/{document_id}` — `backend/src/api/routers/deadline.py:16-40` calls `run_deadline_pipeline(document_id, text, db)` at line 39. Router is registered: `backend/src/api/routes.py:88` (import) and `routes.py:119` (`app.include_router(deadline_router)`).
- **Reachable in prod?** Yes, in principle. Auth is `require_api_key` (`deadline.py:16`, dep at `backend/src/api/dependencies.py:8-14` — flat `x-api-key == settings.API_KEY` check, no payment gate; `check_access` is not involved). Errors write nothing: failure modes are 404 (doc missing), 422 (`document_text` empty — `deadline.py:33-37`), or per-row swallowed insert errors logged at `pipeline.py:245`.
- **No other caller exists.** Nothing in `/upload` or `/process/{session_id}` invokes the pipeline; it is not a post-processing step. Grep for `run_deadline_pipeline` finds only `deadline.py:23` (VERIFIED). Extraction also runs in `backend/evals/run_all.py:197`, but the eval harness never writes to prod tables.

### deadlines — VERIFIED
- **Writer:** `backend/deadline/pipeline.py:195-207` — `db.client.table("deadlines").insert({... "reminder_state": "pending"})`, one row per computed deadline, same trigger as above (only path).
- Insert failures are caught and only logged (`pipeline.py:209-210`) — the endpoint still returns 200 with `deadlines_written: 0`, so a prod schema/constraint failure would be **silent to the user** (consistent with audit S3 "silent failures" theme).

### reminders (actual table name: `deadline_reminders`) — VERIFIED
- **Writer:** `backend/src/api/routers/reminders.py:100-105` — `db.client.table("deadline_reminders").insert(...)` inside `POST /api/reminders/process` (`reminders.py:29`, `require_api_key`). The same handler also updates rows at `reminders.py:133,149` and flips `deadlines.reminder_state` at `reminders.py:117,173`.
- **Trigger:** hourly pg_cron HTTP call (docstring `reminders.py:1-10`; cron SQL in §2 below). **No backend or frontend code calls this endpoint** — its only intended caller is the database cron job.
- **Reachable in prod?** The *endpoint* is deployed (router registered `routes.py:100,121`), but (a) nothing calls it, and (b) if called, Step 3 inserts would fail against the absent `deadline_reminders` table — the exception is caught per-row (`reminders.py:107-109`) and reported only as `stats["errors"]`.
- Selection precondition: it only processes `deadlines` rows with `reminder_state in ('pending','scheduled')` (`reminders.py:62-72`) — and there are 0 such rows, so even a working cron would be a no-op today.

### push_tokens — VERIFIED
- **Writer:** `backend/src/memory/db.py:90` (`save_push_token`, upsert into `push_tokens`), exposed only via `POST /user/{user_id}/push-token` (`backend/src/api/routes.py:247-249`).
- **Trigger:** intended for the Expo mobile app registering its push token. **The React Native app does not exist** (AUDIT_FINDINGS §4.12: "React Native (Expo) ✅ DEPLOYED over an empty directory"). Grep of `frontend/src` finds zero calls to `/push-token` (VERIFIED). → **code path with no caller; 0 rows is the permanent expected state** until a mobile client ships.
- Consequence for delivery: `NotificationService.deliver` (`backend/src/core/notifications.py:110-123`) tries push first, falls back to email — and email is an honest stub (`notifications.py:83-103`: logs "reminder NOT delivered" unless `EMAIL_PROVIDER` is set, and even then "send path not implemented"). So with 0 push tokens, **every fired reminder would end state `failed`** (`reminders.py:147-158`).

## 2. The cron/scheduler mechanism

- **pg_cron enablement:** `supabase/migrations/20260519202000_phase_1_enable_pg_cron.sql:3` (`create extension if not exists pg_cron`). VERIFIED in repo; whether it ever ran against prod is UNVERIFIED (needs dashboard/`cron.job` query).
- **The reminder cron:** `supabase/migrations/20260519230000_phase_6_deadline_reminders.sql` does BOTH things in one file:
  - lines 3–27: `create table public.deadline_reminders` + RLS + indexes;
  - lines 29–43: `cron.schedule('process-deadline-reminders', '0 * * * *', ...)` which does `net.http_post(url := current_setting('app.backend_url', true) || '/api/reminders/process', headers := ... 'X-API-Key' current_setting('app.api_key', true))`.
- **Cross-reference with prod:** `deadline_reminders` is ABSENT in prod (orchestrator fact: PostgREST 404). Since table and cron job live in the same migration, **the cron job was necessarily never scheduled either.** This is the unapplied migration.
- **Config mismatch (design defect, not just an ops gap):** the cron SQL reads Postgres GUCs `app.backend_url` / `app.api_key` via `current_setting(...)` (`20260519230000...sql:34,38`; same pattern in `20260519211000_phase_2_change_detection_job.sql:11,15` and `20260519221000_phase_3_refresh_cron.sql:8`). **No migration in the repo runs `ALTER DATABASE ... SET app.backend_url`** (grep across `supabase/` — zero hits for setting these GUCs; VERIFIED). Prod instead has an `app_config` **table** with keys `backend_url` and `api_key` — and grep across `supabase/` + `backend/` finds **zero references to `app_config`** outside a third-party lib in `.venv` (VERIFIED). So the values exist in prod, but in a table nothing reads; the cron reads GUCs nothing sets. Even applying the migration as-is would produce an hourly `net.http_post(url := NULL || '/api/reminders/process')` no-op.
- **Third dependency:** the job calls `net.http_post` (pg_net). No migration enables the `pg_net` extension — the only mention is a comment in `20260519211000...sql:2` (VERIFIED). Supabase often has pg_net available, but nothing in the repo guarantees it (UNVERIFIED for prod).
- Side note (INFERRED risk, worth knowing for the smoke test): `20260519203000_phase_1_retention_jobs.sql:6-15` schedules a job that nulls `documents.document_text` 30 days after upload. If that job IS live in prod, most of the 45 existing documents would now 422 at `deadline.py:33-37` ("no extractable text") — smoke-test with a **fresh** upload, not an old document.

## 3. The client chain (frontend)

Flow, VERIFIED end to end in `frontend/src`:

1. **HomeHub → Upload:** `pages/HomeHub.tsx:38` tile links to `/upload` (route: `App.tsx:55` → `UploadFlow`).
2. **UploadFlow:** `pages/UploadFlow.jsx:57` `POST /upload` (hardcoded `user-id: proto_user_001`, `email: proto@example.com` — `UploadFlow.jsx:60-61`), then line 83 `POST /process/{session_id}`.
3. **Payment gate:** `UploadFlow.jsx:7-8` — `PAYMENTS_ENABLED = import.meta.env.VITE_PAYMENTS_ENABLED === "true"`, baked at build. The paywall redirect (`UploadFlow.jsx:89-93` → `/pay/:documentId`) fires **only** if `PAYMENTS_ENABLED && processRes.status === 402`; server-side, `check_access` (`backend/src/payments/__init__.py:7`) returns allow when `settings.PAYMENTS_ENABLED` is false (`backend/src/core/config.py:37-38`, default false). **With payments off there is NO dead-end** — line 105 navigates straight to `/results/{documentId}`.
4. **ResultsPage (`pages/ResultsPage.jsx`):** the deadline call is **lazy and user-initiated**. Clicking the "Deadlines" tab (`ResultsPage.jsx:182`) triggers `loadDeadlines()` (`ResultsPage.jsx:84-87`): GET `/api/deadline/{id}/deadlines` (line 15); if 0 rows and not yet attempted this session, POST `/api/deadline/analyze/{id}` (line 67), then re-GET. This is the **only** frontend invocation of the pipeline (grep VERIFIED). Nothing creates trigger_events directly from the client; only the analyze endpoint does.
5. **Timeline:** the Deadlines tab was added 2026-06-09 (commit `b523537`, VERIFIED via git log). Documents uploaded before whatever frontend deploy followed it could never have triggered analyze. Whether the currently deployed `appealing-victory` build includes it, and whether `VITE_API_KEY` in that build matches Railway's `API_KEY` (a 401 at `dependencies.py:13` would surface only as the tab's generic "Couldn't load deadlines (status 401)" — `ResultsPage.jsx:308` — and write nothing): **UNVERIFIED**.

So: **not a paywall dead-end.** The flow reaches the analyze call, but only if a user (a) uses a post-2026-06-09 frontend build, (b) clicks the Deadlines tab, and (c) the request authenticates and the pipeline's DB inserts succeed. 0 rows says that conjunction has never held. Which leg failed cannot be proven from the repo alone (INFERRED candidates, in likelihood order: tab simply never clicked on a current build / deployed build predates the tab; VITE_API_KEY↔API_KEY mismatch; runtime failure of ANTHROPIC key or insert silently swallowed at `pipeline.py:209,245`).

## 4. Ranked list of breaks

| # | Break | Type | Evidence |
|---|-------|------|----------|
| 1 | **`/api/deadline/analyze` never successfully invoked** — the only writer of trigger_events/deadlines is a lazy, click-gated frontend call (shipped 2026-06-09) with silent-failure inserts; 45 docs, 0 rows | (e) unexercised/unproven path — possibly (c)-adjacent (deployed-build lag or key mismatch), **not** (d): no paywall dead-end with payments off | `deadline.py:16-40`; `pipeline.py:195-210,242-246`; `ResultsPage.jsx:64-72,84-87`; commit `b523537` |
| 2 | **`deadline_reminders` table absent in prod** — reminder processor cannot persist anything | (a) unapplied migration | `20260519230000_phase_6_deadline_reminders.sql:3`; prod 404 (orchestrator) |
| 3 | **Cron job never scheduled** (same unapplied migration) → `/api/reminders/process` has zero callers | (a) unapplied migration + (c) code path with no caller | same file, lines 29-43; `reminders.py:29` |
| 4 | **Cron config never wired even in design**: job reads GUCs `app.backend_url`/`app.api_key` that no migration sets; prod's `app_config` table is read by nothing; pg_net never enabled by migration | (b) missing app_config/GUC keys + (e) config-mechanism mismatch | `...sql:34,38`; zero repo refs to `app_config`; zero `ALTER DATABASE ... SET app.*`; zero `create extension pg_net` |
| 5 | **push_tokens has no caller** — endpoint exists for a mobile app that is an empty directory | (c) code path with no caller | `routes.py:247-249`; `db.py:83-97`; AUDIT §4.12 |
| 6 | **Email delivery is a stub** — even a fired reminder ends `failed` (no push tokens + no provider) | (e) stub | `notifications.py:83-123`; `reminders.py:147-158` |

Break #1 is first: nothing downstream (2–6) can ever execute until a `deadlines` row exists with `reminder_state='pending'`. Breaks 2–4 then all block the reminder half independently — fixing any one of them alone changes nothing.

## 5. What a fix would require (described, not implemented)

**Order matters; each step gates the next.**

1. **Prove the upstream half with a supervised prod smoke test (S2-5's own recommended action, no code change needed if it passes):**
   - Fresh upload via the live frontend (fresh — retention job may have nulled old `document_text`); confirm `/process` returns 200 and `documents.document_text` is non-empty.
   - Click the Deadlines tab (or curl `POST {backend_url}/api/deadline/analyze/{document_id}` with the real `X-API-Key`); capture the JSON — `trigger_events_written` / `deadlines_written` must be > 0, and check Railway logs for the swallowed-insert errors from `pipeline.py:209,245`.
   - Verify rows: `select count(*) from trigger_events; select id, reminder_state from deadlines where document_id = ...` (expect `reminder_state='pending'`).
   - If the tab path fails but curl succeeds → frontend build/key issue (`VITE_API_KEY` vs Railway `API_KEY`); if both fail, the error is now visible instead of silent.
2. **Apply the reminder migration — but fix its config mechanism first.** Decide ONE of: (i) set the GUCs the SQL already reads (`ALTER DATABASE postgres SET app.backend_url = '<railway url>'; ... app.api_key = ...` — note the api_key then lives in the DB config, same exposure as the existing app_config table), or (ii) amend the cron SQL to read from the existing `app_config` table (a `select value from app_config where key='backend_url'` subquery). Then, in order: `create extension pg_net` (verify availability), confirm pg_cron enabled (`20260519202000`), apply `20260519230000` (table + RLS + cron). Per DECISIONS.md standing rules this goes through the verified migration mechanism (blocked-on-Joe item) and S3-1's parity check should confirm application. Same GUC fix applies to the phase_2/phase_3 cron jobs, which have the identical dead config read.
3. **Verify the cron half:** after one hour (or manual `select cron.schedule` run / direct curl of `POST /api/reminders/process` with the API key), expect `deadline_reminders` rows for the smoke-test deadline, `deadlines.reminder_state` → `scheduled`, and — until email/push exist — fired reminders ending `failed` with the honest log line from `notifications.py:92-95`. That `failed` is correct current behavior, not a new bug.
4. **Delivery (separate items, per audit):** wire Resend (`notifications.py:98` TODO) for web users; push tokens stay 0 until a mobile client exists — that is expected, not a defect to "fix" now.
5. **Non-blocking but recommended before advertising the feature:** make the two silent insert failures loud (`pipeline.py:209,245` currently log-and-continue while returning 200) and fix the S1-4 IDOR on the two unauthenticated deadline GETs (`deadline.py:43,62`) before more real deadline data lands.

## Evidence classification

- **VERIFIED (read at cited lines):** all file:line claims above — writers, triggers, router registration, cron SQL, GUC reads, absence of `app_config`/`ALTER DATABASE`/`pg_net` references (greps over repo), frontend flow including paywall branch and lazy analyze, notification stub, commit `b523537` date.
- **INFERRED (reasoned, not executed):** which leg of break #1 actually failed (never-clicked vs build-lag vs key mismatch vs runtime error); that retention job may have nulled old docs' text; that reminders would all end `failed` today.
- **UNVERIFIED (needs network/dashboard):** current deployed frontend build contents; Railway `API_KEY`/`VITE_API_KEY`/`ANTHROPIC_API_KEY` values; whether pg_cron/pg_net extensions and any `cron.job` rows exist in prod; whether the retention jobs are live; prod row counts (taken as given from orchestrator).

# CORRECTION (2026-08-14) — diagnosis report break #2 was wrong

Break #2 of this report ("deadline_reminders table absent in prod — migration
unapplied") is INCORRECT. The table name was checked as `reminders`; the actual table
is `deadline_reminders` (migration 20260519230000_phase_6_deadline_reminders.sql, a
Phase-6 May migration). REST probe on 2026-08-14: deadline_reminders returns HTTP 200,
count 0 rows. The table, its RLS policy, and its indexes exist in prod; the Phase-6
migration WAS applied, including its `select cron.schedule(...)` for the hourly
/api/reminders/process call.

Revised understanding of the reminder half:
- Table: EXISTS (0 rows). Not a blocker.
- Cron job: scheduled by the applied migration, but reads Postgres GUCs
  (`app.backend_url` / `app.api_key`) that were never set — the hourly job either
  fails to resolve its URL or posts with NULL config. Config-mechanism blocker stands
  (recorded decision: amend SQL to read app_config).
- pg_net: net.http_post requires the pg_net extension (Supabase default) — verify
  when SQL access is available.
- Email delivery remains a stub (break #6 stands).

Net effect on the fix sequence: unchanged (amend config SQL → reschedule cron → verify
pg_net), minus the table-creation step. Record corrected per S3-1 parity check.
