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
