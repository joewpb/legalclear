# Follow-ups

- S1-3: upsert-by-email in `attorney_referral.py:upsert_user` still overwrites an
  existing profile found by client-supplied `email` with no verification (e.g. email
  ownership confirmation). Out of scope for this fix per DECISIONS.md; needs a
  verification step (e.g. magic link) before it can upsert by email.
- S1-3: `/api/attorney-referral/intake` and `/submit` are also named in-scope by the
  audit but were NOT gated with `require_api_key` in this fix — the shipped frontend
  caller (`AttorneyReferralFL.tsx`) calls them with raw `fetch()` and no `X-API-Key`
  header, so adding the dependency would 401 the live chat/submit flow. Fixing this
  requires a coordinated frontend change (send the key, or switch to the `api.js`
  axios client) — reported instead of coded per scope rules.

## S1-3b (new triage item)

Finding verbatim (from item 4 run): "/api/attorney-referral/intake and /submit are also
named in-scope by the audit but were NOT gated with require_api_key in this fix — the
shipped frontend caller (AttorneyReferralFL.tsx) calls them with raw fetch() and no
X-API-Key header, so adding the dependency would 401 the live chat/submit flow. Fixing
this requires a coordinated frontend change (send the key, or switch to the api.js axios
client)."

Dependency: S1-3b must not be scheduled until S1-5 (PII/DeepSeek) is decided — it
touches the same intake path.

## S3-5d (new triage, from S2-5 diagnosis)
`backend/deadline/pipeline.py:209,245` swallow DB insert errors while the endpoint
returns 200 with `deadlines_written: 0` / no error. Seventh silent-failure site, same
class as Group B (S3-5). Makes "endpoint never called" indistinguishable from "called
and failed silently" — which is exactly the ambiguity blocking the S2-5 smoke test.
Fix before or alongside any deadline-pipeline work.

## S2-6 — /api/analyze/* dead or broken
Deletion deferred to Group E per standing rules ("no deletions during Phase 2").
Do not act until Joe explicitly schedules Group E.

## Cron config decision (recorded 2026-08-14)
Amend the reminder cron SQL to read the `app_config` table rather than setting
Postgres GUCs (`app.backend_url` / `app.api_key`). Rationale: GUCs are unmanaged,
unversioned state that no migration sets and that vanish on restore; app_config is
migratable, inspectable, and already holds the parked values in prod.
Sequence: S3-1 parity check → apply the migration → amend the SQL → enable pg_net →
schedule the cron. (Phase 2/3 cron jobs carry the identical dead GUC read and get the
same treatment.)

## S2-1 follow-up — /attorney-referral has no main-nav tile (found during S2-2)
Pre-check for S2-2 confirmed `/attorney-referral` (App.tsx:92) has the same
inbound-link gap as `/find-legal-help` did: no HomeHub tile, no Navbar entry, no
site-wide footer (none exists). Its only inbound link is from the
`LEGAL_AID_LINKS` list rendered inside `CaseLawLookupFL.tsx`'s disclaimer section
— not discoverable from the home hub. Belongs to S2-1, not S2-2 (S2-2 scope is
`/find-legal-help` only. Needs its own HomeHub tile or nav entry.

## S2-5 follow-up — token_estimate key also nonexistent (routes.py:288)
Same class as S2-5a: the upload handler reads `doc.get("token_estimate", 0)` but the
ingestion return dict has no such key, so sessions are created with token_count=0.
Bookkeeping only — does not affect document text or the pipeline. Fix with any future
upload-handler work.
## S2-5 follow-up — legacy documents: 422 with no explanation (smoke test finding)
Returning users opening the Deadlines tab on a pre-S2-5a document get a 422 (no
extractable text) with no explanation. The 45 legacy documents' original files are
unrecoverable (no storage bucket for uploads — Supabase Storage holds court-forms only;
text was never stored due to S2-5a). Needs a clear empty-state message telling the user
to re-upload. Not a silent failure — currently it IS a silent 422.
## UPL follow-up — third parallel disclaimer text found (S2-5c smoke test)
`backend/src/api/routers/deadline.py`'s analyze response carries a disclaimer with
EXTERNAL links (floridalawhelp.org, floridabar.org) — contradicts the no-external-links
rule. This is the THIRD parallel disclaimer text in the codebase (alongside
`get_disclaimer` and `apply_disclaimer` from the S1-6 report). Direct evidence for
consolidating on a single `apply_disclaimer` source rather than patching each site.
Added to the UPL fix footprint.
## S2-3 REOPENED — correction (2026-08-14, closure-table verification)
Earlier resolution "S2-3 already applied — 9 rows ✓" was WRONG. The 9 prod rows are the
May Phase-3 STATEWIDE holiday seed (20260519220500, circuit=0 only, created 2026-05-19).
The Aug 8 local-closures seed (20260808000000_seed_local_court_closures.sql — 99 rows,
circuits 1–20, 2026-01-02 through 2027-12-27) has NEVER been applied to prod: 0 rows
with circuit != 0. Sources exist and are intact: the migration, its raw scan output at
backend/src/data/court_closures_seed.json (99 closures, all 20 circuits, no runtime
loaders), and docs/court-closures-florida-2026.md. Gap: 99 local-holiday rows missing
across every circuit. Reopen pending the migration mechanism decision (see S3-1).

## BLOCKER — RESOLVED 2026-08-14: closure table complete (kept for the record)
Court closures are an input to deadline computation. The Aug 8 local-closures seed
(20260808000000_seed_local_court_closures.sql, 99 rows, circuits 1–20) was applied
MANUALLY via the REST API on 2026-08-14 with ON CONFLICT DO NOTHING semantics
(ignore-duplicates). Verified: 9 → 108 rows, all 20 circuits represented, spot-checks
against docs/court-closures-florida-2026.md matched. The deadline pipeline may now
proceed for supervised use.
Still open: the application was manual (REST), not through any migration mechanism —
the S3-1 migration-mechanism question remains open and the seed is idempotent, so it
must be re-applied through whatever mechanism is settled on. The attorney-referral
tables migration remains BLOCKED on RLS (unchanged).
## CORRECTNESS BLOCKER — S2-7: deadline anchor uses issuance date, not service date
Fla. Stat. § 83.60(2) runs the tenant's 5-day answer period from SERVICE OF PROCESS,
not from the date the summons was issued or signed. The Aug 14 smoke test extracted
"DATED this 14th day of August, 2026" — an issuance line — and computed Aug 21 from it.
Service commonly occurs days after issuance; computing an eviction answer deadline from
the wrong anchor can produce a default judgment. Same tier as the closure blocker —
pipeline must not serve real users until resolved.
Scope: (a) does the extractor distinguish issuance date, service date, and hearing date,
or treat any date as interchangeable? (b) does each deadline rule declare which anchor
it requires? (c) when the required anchor is absent the pipeline must skip and escalate,
never substitute a different date.

## S2-5 follow-up — filing count silently broken since v1 (found 2026-08-14)
`count_filings` (db.py:282) and `record_filing` (db.py:301) swallow the
missing-table exception, so the one-free-filing paywall gate (routes.py:425) can never
fire and filing history is silently dropped. Inert only because PAYMENTS_ENABLED is
off. Unblocks when the 20260704 filings migration is applied; gate behavior should be
re-verified the day payments enable.

## S3-1 follow-up — app_config is unmanaged schema (parity finding)
public.app_config exists in prod but in NO migration file. Verified 2026-08-14: anon-key
read returns 200 with empty rows (RLS filtering — rows not exposed); nothing in the repo
reads it over REST. Belt-and-suspenders if it ever holds a live key: revoke all on
public.app_config from anon, authenticated (cron runs as postgres — unaffected), and
create a migration for the table so it stops being invisible to the parity check.
- This fix will crash Railway (`zesty-delight`) on next deploy if `API_KEY` is unset in Railway env — confirm it's set there before merging/deploying (see DECISIONS.md S1-1 verification-half note).
