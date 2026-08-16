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
## DO NOT MERGE — origin/fix/extract-hallucinated-date-49 (c00c698)
Fully superseded by S2-5c (merged as bb0dcfd). Merging it would delete the
ordinal-date support in _date_appears_in_text and re-break the eviction-summons parse
(the original smoke-test failure). Verified: its extract.py is main's extract.py minus
exactly the ordinal block (13 deletions). Leave the branch as a record; never merge.

## DEFERRED — fix/pc-upl-stale-tests (71601f4) → Phase B4
Dropped from Phase A (2026-08-15) without resolution. It rewrites test_pc_upl.py to
import get_disclaimer from src/core/upl.py with signature ("standard", "en"),
against src/core/disclaimer.py's ("en", "standard"). Main's UPL surface moved under it
(s3-5c-upl-swallow), so both sides now edit overlapping regions of the same test file.
Resolving it requires choosing the canonical disclaimer source, which is Phase B4's
decision (B4 consolidates on apply_disclaimer across all three known parallel
disclaimer texts). Expect this branch to be rewritten rather than merged once B4 lands.
## B5 — service date capture (scoped 2026-08-15 from Decision 2; NOT dispatched)
G1 does not open until B5 ships. Decision 2 verbatim:
- Service date stored with provenance `user_supplied`, never extracted. Distinct field,
  distinct audit trail. It must never be recorded as an extracted fact.
- Deadline presented conditionally: "If you were served on X, your response is due Y."
- Input remains visible and editable; correction recomputes the deadline.
- "I don't know" escalates and does NOT compute. Tell the user the return of service is
  filed with the clerk and the case docket shows the service date.
- Ask HOW service occurred, not only when. Fla. Stat. § 48.183 permits service by
  posting when the tenant cannot be found; a tenant who found papers on the door may
  not know the actual service date. Method affects the analysis.
Requires UI work (service-date prompt, method question, validation, provenance field) —
multi-surface, to be split per the standing dispatch rules when scheduled.
## CORRECTION (2026-08-15) — the "third parallel disclaimer" was a misdiagnosis
Re-examined during B4b-0 scoping: backend/src/api/routers/deadline.py has NO inline
disclaimer text (verified — no floridalawhelp/floridabar references in the file). The
external links seen in the smoke-test analyze response were apply_disclaimer's OWN text
(src/core/upl.py:37-56) surfacing through deadline.py's apply_disclaimer call. Real
state: TWO parallel disclaimer sources — get_disclaimer (src/core/disclaimer.py:74) and
apply_disclaimer (src/core/upl.py), both carrying external links — plus two agent
prompts that instruct the LLM to print floridalawhelp.org (explainer.py:35,
form_guide.py:23). B4's consolidation target is unchanged (apply_disclaimer canonical);
the "third parallel text" claim in the UPL follow-up above is superseded by this.
## S1-adjacent — model-level external-link emission (found B4b-1a, 2026-08-15)
Prompt edits removed the floridalawhelp.org INSTRUCTIONS, and the instructed closing
line now correctly reads "Free help: LegalClear /find-legal-help" (verified live).
But live agent runs against representative inputs show the model still emits external
URLs from training knowledge, unprompted:
- explainer.py spontaneously added a `free_resources` field (not in the prompt schema):
  clsmf.org, orangecountybar.org, flcourts.gov, 211 Florida.
- form_guide.py invented `where_to_file.online_url = https://myflcourtaccess.com` (the
  prompt does ask for that field, but the URL is model-invented and unvetted).
This is NOT fixable by prompt edits and needs a decision: post-processing
filter/allowlist on agent output (recommended shape: strip any URL not on an explicit
allowlist; keep /find-legal-help), vs accept-risky-emission with logging. Severity:
UPL/CORRECTNESS-adjacent — external legal-aid links the site promised to eliminate.
(Note: the disclaimer-field links seen in the same test run are pre-existing
disclaimer.py text, already fixed by B4b-1 canonicalization on its branch — not this
finding.)
## S2-5/UPL follow-up — deadline router error paths carry NO disclaimer (B4b-2, 2026-08-15)
deadline.py's GET /deadlines and GET /trigger-events except blocks (:62-64, :82-84) and
all HTTPException raises return only {"detail": "..."} — no disclaimer key. Only happy
paths carry one. Pinned by test_deadline_disclaimer.py (error-path absence asserted
deliberately). If error-path disclaimers become required (B4 typed-event goal or UPL
audit), this is the gap. Decision owed: is a bare-error response UPL-acceptable, or
must errors carry the disclaimer too?
## B5-f3 — trigger_events.user_* columns deprecated, not dropped (2026-08-16)
document_service_facts (supabase/migrations/20260815000002_b5f3_document_service_facts.sql)
now holds user-supplied service facts; trigger_events.user_service_date,
user_service_method, and service_date_provenance are no longer read or written by
any production code path (src/api/routers/deadline.py, deadline/pipeline.py,
src/memory/db.py — the old get_user_supplied_service_date/set_user_supplied_service_date
methods are kept, unused, marked DEPRECATED). The columns themselves were left in
place intentionally — dropping them is Phase G's job, and should happen alongside
confirming nothing else (dashboards, ad-hoc queries) still reads them.
## B5-f4 follow-up — extraction returned the hearing event duplicated (2026-08-16)
Document 56703e4b-a3b0-4ea6-aeb8-3334b7431274: Stage 1 extraction returned the SAME
hearing trigger event effectively twice (an "issued" event on 2026-08-14 and a
"hearing"/served-anchored event on 2026-08-28 that duplicated the answer-deadline
anchor), which is why the eviction answer deadline was computed and written twice
before this fix. B5-f4 dedups the write path structurally (one row per governing_rule
per document, regardless of how many trigger events produce it) so this no longer
double-writes, but the underlying extraction defect — why extract_trigger_events
returned a duplicated/redundant event for this document — is untouched and out of
scope for this fix. Needs its own investigation of extract.py's prompt/parsing for
this input.
