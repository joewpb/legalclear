# Follow-ups

CONVENTIONS (Decision 21 — enforced by scripts/verify_slist.py, CI job
verify-slist):
- Every entry heading: `## <ID> — <STATE> <title>` with STATE ∈ OPEN,
  OPEN (deliberate), RESOLVED, RECORDED, DEFERRED.
- A commit that fixes an entry declares `fixes <ID>` in its subject.
- An OPEN entry whose fix commit lands without closing the entry FAILS CI:
  close it (RESOLVED + evidence) or mark OPEN (deliberate) with a reason.
- RECORDED = diagnosis/report kept for the record, not a work item.
  DEFERRED = paused/phase-deferred on purpose. RESOLVED entries stay in the
  file for the record; the gate only guards OPEN ones.

## ES-I18N — RECORDED ES i18n audit — recorded-not-scheduled (2026-08-23, Decision 16)
The Spanish-language i18n audit item is deferred by Decision 16: English first; Spanish stays out of scope until the English product is complete and live. The language parameter remains wired end-to-end (AGENTS.md §7 — no re-architecture required); this is deferral, not removal. Re-open with Decision 16.

## PA-NOEST — DEFERRED PA 60-day no-estimate cancellation variant — named, not shipped (2026-08-22, I-3c)
§ 626.854(7) also permits cancellation without penalty if the public adjuster fails to provide a written estimate within 60 days of contract execution. The 10-day and emergency later-of clocks shipped in I-3c; the 60-day variant interacts with the estimate-delivery tracking path and was left out of the I-3 scope. Named-not-shipped; add when estimate tracking exists.

## PC-NOI — OPEN pc_notice_of_intent anchored on date_of_loss — proxy for a "before filing suit" gap (2026-08-22, I-3 Job 1 report)
`pc_notice_of_intent` (§ 627.70152) is computed as date_of_loss + 10 business days, but the statute defines it as a minimum gap BEFORE filing suit — the true deadline depends on the (unknown) suit-filing date, not the date of loss. The current computation is a conservative floor and is declared statutory-business under the counting-regime mechanism (Job 2, 2026-08-22), but the anchor is approximate by design. An approximate anchor on a user-facing deadline is the kind of thing that reads as precise to a user — recorded here so it stays visible. Recorded-not-scheduled (Joe, 2026-08-22).

## CIT-GAP — RESOLVED Citation filter regex gap — singular "Florida Statute N" passes unfiltered (2026-08-20, found by I-1 live proof; fixed cdebb50 with the 626.9541 locked test)
`citation_filter.py` `_CITATION_TOKEN_RE` (:114-120) matches `"Fla. Stat. §"`, `"Florida Statutes"` (plural), and bare `"§"` — but NOT singular `"Florida Statute 627.70131"`. The I-1 live emission run showed the model naturally phrases citations that way; those strings pass through the filter with no curated-set check at all. In that run the content happened to be correctly scoped, but the filter's guarantee (Decision 4 — deterministic code guarantees what prompts can't) does not cover this phrasing, so a fabricated singular-form citation would survive. The prompt instructs the `"Fla. Stat. §"` format, which is not a guarantee. Same class: regulatory cites (`Florida Administrative Code Rule 69O-166.031`) are not matched by the filter's statute path either. Fix shape: extend the token regex alternation + tests (fabricated singular-form citation must be stripped). CLOSED at cdebb50 (G1: 46 live-collected phrasings, 12 tests, incl. singular
"Florida Statute 626.9541" stripped — test_spelled_out_singular_uncurated_stripped).
2026-08-27 test-integrity finding (fixed): test_citation_phrasings.py depended on
test_citation_filter.py's module-level registration of 'test-agent' — order-dependent
coupling. Targeted runs failed 12/12 on the registry's raise-on-unknown path while
full-suite runs passed; the fixture-missing path also returned early (silent skip).
Fixed: registration is now in-file and a missing fixture raises loudly. 35/35 green.

## CHK4-DEBT — RESOLVED Checker check-4 debt — 7 frontend disclaimer duplicates (2026-08-20; retired 2026-08-22 — canonical DisclaimerNote imported, Decision 15 job)
Decision 3 makes `apply_disclaimer` canonical; the checker's check 4 still flags 7 frontend pages hardcoding their own disclaimer string: `LandlordTenantFL.tsx:110`, `PoliceReportAnalyzer.tsx:992`, `PropertyCasualtyExplainer.tsx:510`, `SmallClaimsExplainer.tsx:447`, `SmallClaimsFL.tsx:46`, `TrafficFL.tsx:57`, `WillsTrustsExplainer.tsx:615`. This is the standing checker BASELINE (7 violations across 6 checks). Not blockers; the pages must consume the canonical disclaimer (backend-provided) or the checker baseline must be amended by decision. Recorded-not-scheduled.

## ORIN-RULES — RECORDED Orin staged rule sets — loaded decision, unloaded remainder (2026-08-20; superseded by S1-2C)
Orin's 2026-08-18 harvest staged 9 rule sets. Loaded to `court_rules`: criminal 3.x (156), small_claims 7.x (25), general_practice 2.x (57 incl. 2.514), civil_procedure 1.280–1.400 (14). Staged but deliberately NOT loaded: traffic (43), juvenile (207), svp_commitment (25), and fuller appellate (55) + probate (123) parses. Reasoning: the substantive sets already in prod are verified against official PDFs (Decision 14 best-side merge applied), and loading Orin's other parses would replace verified text with unverified text; the FORM rows were routed to `court_forms` instead (22 inserted, 8 skipped). Staged files remain on Orin at `~/legal_data/fl_harvest/data/stage/`. Revisit only if traffic/juvenile/svp modules ever exist.

## JSON-AUDIT — RESOLVED Intermittent JSONDecodeError in structured-output parsing — AUDITED 2026-08-30, swept by Decision 20 (cc07e48)
Investigation done (which agents parse JSON how, retry-once wired, repair fallback):
COMPLIANT (retry/recovery wired): intake.py (retry loop + tightened prompt),
classifier.py (2 attempts + _default), deadline/extract.py (2 attempts + schema
validate + escalate), scanner.py (parse_json_list/_dict = deterministic substring
recovery), opinion_retrieval attorney questions (parse_json_array + one retry,
fixed 2651869).
NO-RETRY, graceful degrade (strip-fences only; intermittent failure = degraded
response, no crash): police_report_v2 (risk skipped), property_casualty (payload
skip/error event), discovery_motion (risk skipped), criminal_procedure (opinions
skipped), small_claims (citations []), expungement, risk_scanner, form_guide,
explainer (error dict), pc_llm_tap, orin_opinions (regex fallback, also hand-rolled
fence-strip — same pattern the Haiku function had).
COUNT: 11 sites across 11 files missing retry-once. FIX SHAPE (deterministic, ZERO
extra LLM cost): swap `json.loads(strip_markdown_fences(x))` for
json_utils.parse_json_list/parse_json_dict/parse_json_array — the shared
_parse_with_retry does fence-strip + largest-substring recovery, satisfying
AGENTS.md §5 retry-once without another model call. Sweep pending Joe's go.

## RATE-LIMIT — RESOLVED Upload pipeline has no rate limit (2026-08-20) — RESOLVED 2026-08-27 (STALE ENTRY, NOT A REGRESSION)
Landed at 167c5ad the same day the entry was written: `@limiter.limit("10/minute")` on
`upload_document` (routes.py:253), slowapi exception handler registered, locking tests
(test_upload_text_key, test_upload_token_estimate) use a real starlette Request — 3/3 green.
LIVE-VERIFIED 2026-08-27: 12 rapid junk POSTs to prod /upload → 200 x10, then 429 x2 — the
10/min limit is active in prod. How a closed item re-entered the list: the entry was written
by the Aug 20 rate-limit enumeration audit (85d19cb) BEFORE the fix landed hours later, and
the close was never back-annotated — ledger hygiene, not a code regression. (Probe side-note:
no-file uploads return HTTP 200 with an error payload instead of 422 — separate API-hygiene
observation, not in scope.)

## S1-3 — DEFERRED upsert-by-email in `attorney_referral.py:upsert_user` still overwrites an
  existing profile found by client-supplied `email` with no verification (e.g. email
  ownership confirmation). Out of scope for this fix per DECISIONS.md; needs a
  verification step (e.g. magic link) before it can upsert by email.
- S1-3: `/api/attorney-referral/intake` and `/submit` are also named in-scope by the
  audit but were NOT gated with `require_api_key` in this fix — the shipped frontend
  caller (`AttorneyReferralFL.tsx`) calls them with raw `fetch()` and no `X-API-Key`
  header, so adding the dependency would 401 the live chat/submit flow. Fixing this
  requires a coordinated frontend change (send the key, or switch to the `api.js`
  axios client) — reported instead of coded per scope rules.

## S1-3B — OPEN new triage item

Finding verbatim (from item 4 run): "/api/attorney-referral/intake and /submit are also
named in-scope by the audit but were NOT gated with require_api_key in this fix — the
shipped frontend caller (AttorneyReferralFL.tsx) calls them with raw fetch() and no
X-API-Key header, so adding the dependency would 401 the live chat/submit flow. Fixing
this requires a coordinated frontend change (send the key, or switch to the api.js axios
client)."

Dependency: S1-3b must not be scheduled until S1-5 (PII/DeepSeek) is decided — it
touches the same intake path.

## S3-5D — RESOLVED (triage, from S2-5 diagnosis) — RESOLVED 2026-08-30 (STALE ENTRY; B5 series fixed it)
Verified in tree: every DB-write failure path now escalates loudly instead of
swallowing — _record_trigger_event docstring cites S3-5d and increments
trigger_events_written ONLY on a landed row, else escalation_needed + "this event is
NOT recorded"; deadline insert failure -> escalation_needed + "NOT recorded and will
not trigger a reminder"; closure fetch failure -> closure_fetch_failed -> every fatal
deadline escalates. The router surfaces escalation_needed/reasons in the response.
Locked by test_trigger_event_insert_failure_does_not_claim_success,
test_deadline_insert_failure_does_not_claim_success, and
test_closure_fetch_failure_escalates_instead_of_silent_compute — 14/14 pipeline tests
green. Entry was never back-annotated after the B5 fix landed — list hygiene.

## S2-6 — OPEN /api/analyze/* dead or broken
Deletion deferred to Group E per standing rules ("no deletions during Phase 2").
Do not act until Joe explicitly schedules Group E.

## CRON-CONFIG — RECORDED Cron config decision (recorded 2026-08-14)
Amend the reminder cron SQL to read the `app_config` table rather than setting
Postgres GUCs (`app.backend_url` / `app.api_key`). Rationale: GUCs are unmanaged,
unversioned state that no migration sets and that vanish on restore; app_config is
migratable, inspectable, and already holds the parked values in prod.
Sequence: S3-1 parity check → apply the migration → amend the SQL → enable pg_net →
schedule the cron. (Phase 2/3 cron jobs carry the identical dead GUC read and get the
same treatment.)

## S2-1 — DEFERRED follow-up — /attorney-referral has no main-nav tile (found during S2-2; attorney referral paused per Decision 19)
Pre-check for S2-2 confirmed `/attorney-referral` (App.tsx:92) has the same
inbound-link gap as `/find-legal-help` did: no HomeHub tile, no Navbar entry, no
site-wide footer (none exists). Its only inbound link is from the
`LEGAL_AID_LINKS` list rendered inside `CaseLawLookupFL.tsx`'s disclaimer section
— not discoverable from the home hub. Belongs to S2-1, not S2-2 (S2-2 scope is
`/find-legal-help` only. Needs its own HomeHub tile or nav entry.

## S2-5-TOKEN — OPEN follow-up — token_estimate key also nonexistent (routes.py:288)
Same class as S2-5a: the upload handler reads `doc.get("token_estimate", 0)` but the
ingestion return dict has no such key, so sessions are created with token_count=0.
Bookkeeping only — does not affect document text or the pipeline. Fix with any future
upload-handler work.
## S2-5-LEGACY — OPEN follow-up — legacy documents: 422 with no explanation (smoke test finding)
Returning users opening the Deadlines tab on a pre-S2-5a document get a 422 (no
extractable text) with no explanation. The 45 legacy documents' original files are
unrecoverable (no storage bucket for uploads — Supabase Storage holds court-forms only;
text was never stored due to S2-5a). Needs a clear empty-state message telling the user
to re-upload. Not a silent failure — currently it IS a silent 422.
## UPL-DISC — RESOLVED follow-up — third parallel disclaimer text found (S2-5c smoke test; misdiagnosis — see DISC-MISDIAG correction 2026-08-15)
`backend/src/api/routers/deadline.py`'s analyze response carries a disclaimer with
EXTERNAL links (floridalawhelp.org, floridabar.org) — contradicts the no-external-links
rule. This is the THIRD parallel disclaimer text in the codebase (alongside
`get_disclaimer` and `apply_disclaimer` from the S1-6 report). Direct evidence for
consolidating on a single `apply_disclaimer` source rather than patching each site.
Added to the UPL fix footprint.
## S2-3 — RESOLVED REOPENED — correction (2026-08-14, closure-table verification; 108 live prod rows verified 2026-08-29 — reopen was stale)
Earlier resolution "S2-3 already applied — 9 rows ✓" was WRONG. The 9 prod rows are the
May Phase-3 STATEWIDE holiday seed (20260519220500, circuit=0 only, created 2026-05-19).
The Aug 8 local-closures seed (20260808000000_seed_local_court_closures.sql — 99 rows,
circuits 1–20, 2026-01-02 through 2027-12-27) has NEVER been applied to prod: 0 rows
with circuit != 0. Sources exist and are intact: the migration, its raw scan output at
backend/src/data/court_closures_seed.json (99 closures, all 20 circuits, no runtime
loaders), and docs/court-closures-florida-2026.md. SUPERSEDED 2026-08-27 (STALE ENTRY): prod court_closures holds 108 rows —
9 statewide (circuit=0) + 99 local (circuits 1-20, all twenty circuits represented),
verified live via REST. The reopen predates the same-day 2026-08-14 manual REST
application recorded in the BLOCKER-RESOLVED entry below; that entry (9 -> 108 rows)
is the accurate state and this reopen should have been struck when it was written.
Still OPEN (unchanged): the manual application must be re-applied through whatever
migration mechanism S3-1 settles on — the seed is idempotent (ON CONFLICT DO NOTHING).

## CLOSURE-BLOCKER — RESOLVED 2026-08-14: closure table complete (kept for the record)
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
## S2-7 — RESOLVED (2026-08-30, ruled by Joe) — deadline anchor now service date, locked
Original entry (2026-08-14): Fla. Stat. § 83.60(2) runs the tenant's 5-day answer
period from SERVICE OF PROCESS, not from the date the summons was issued or signed.
The Aug 14 smoke test extracted "DATED this 14th day of August, 2026" — an issuance
line — and computed Aug 21 from it. Service commonly occurs days after issuance;
computing an eviction answer deadline from the wrong anchor can produce a default
judgment.

RESOLUTION: the entry was written at diagnosis time; the fix landed with the B5
series in 2826fbd ("deadline rules declare required date anchors; never substitute
issuance for service") and the entry was never back-annotated. Current state,
root-verified 2026-08-30:
- Anchor origin: LLM extractor labels each date by kind (deadline/extract.py:28-29
  event_type enum; prompt rules at extract.py:80-84 — "DATED ..." lines are
  'issued', NEVER 'served').
- Rule declaration: deadline/rules.py:92-93 — § 83.60(2) required_anchors
  ("served",).
- Gate: deadline/pipeline.py:231-254 — wrong-kind date with no user-supplied
  service record → escalation_needed, zero deadlines, explicit reason. Never
  substitutes issuance. document_service_facts consulted once before the gate
  (pipeline.py:116, B5-f3).
- Locking tests: tests/test_anchor_gate.py
  (test_issuance_date_never_stands_in_for_service:78,
  test_unknown_event_type_is_not_a_valid_anchor:95,
  test_service_date_computes_normally:101,
  test_every_rule_declares_required_anchors:121) +
  test_deadline_pipeline.py:210
  (test_user_supplied_personal_service_date_wins_over_extracted_issued_date).
  22 passed fresh 2026-08-30.
- List-hygiene class (3rd instance): diagnosis-time entry never closed when the
  fix landed — see the S-list hygiene gate in DECISIONS.md (Decision 21).

OPEN HALF (B5 UI, separate item): when the gate escalates for a missing service
date, the user needs the UI to SUPPLY it — scoped as the next build.

## S2-5-FILING — OPEN follow-up — filing count silently broken since v1 (found 2026-08-14)
`count_filings` (db.py:282) and `record_filing` (db.py:301) swallow the
missing-table exception, so the one-free-filing paywall gate (routes.py:425) can never
fire and filing history is silently dropped. Inert only because PAYMENTS_ENABLED is
off. Unblocks when the 20260704 filings migration is applied; gate behavior should be
re-verified the day payments enable.

## S3-5E — RESOLVED smoke harness recorded failures as passes (silent-check class, 2026-08-24; harness rewritten, second bug caught 2026-08-26)
The Phase I finale smoke (runs/phase-i-autonomous/smoke_test.py) let raw
artifact checks pass on any HTTP status (`expect=None`) and printed ALL PASS
while claim_log/policy_request_letter were 500 in prod and the guide returned
zero deadlines — both real prod defects. Harness rewritten: every call must
declare a status expectation or a content validator; `expect=None` raises.
SECOND BUG in the rewrite, caught 2026-08-26 by reading its own output: the
final tally indexed r[2] (the always-truthy evidence string) instead of r[1]
(the ok flag), so FAIL rows were never counted and it printed ALL PASS with
two live FAILs on screen. Fixed to r[1]. Pattern count: fifth instance (the
harness itself produced two).

CLOSED 2026-08-27 by test-the-tester (Joe's directive): the canonical harness
(scripts/smoke_pc_claims.py) now ships a `--selftest` mode — a stub transport
feeds a KNOWN-FAIL scenario (expect 200 vs delivered 500) plus a
no-expectation call, and the harness must record the failure and raise
respectively. Selftest exits 0 only when the harness fails loudly; CI runs it
via backend/tests/test_smoke_harness.py, so any regression that lets a
failure pass silently now fails the suite. Instance class closed.

## CLUSTER-ID — OPEN Declaration drift — legal_opinions.cluster_id TEXT in repo, INTEGER in prod
20260703020000_legal_opinions.sql and F4 both declare cluster_id TEXT (F4
declares no PK); prod is INTEGER (OpenAPI-probed 2026-08-24). parity_check.py
diffs column NAMES only, so this drift is invisible to the nightly net. The
citation_treatment FK added in 20260824000002 assumes prod's integer/integer
and will FAIL on a fresh database replay of the migration set. Align
declarations to prod (INTEGER) in a dedicated pass.

## S3-1 — OPEN follow-up — app_config is unmanaged schema (parity finding)
public.app_config exists in prod but in NO migration file. Verified 2026-08-14: anon-key
read returns 200 with empty rows (RLS filtering — rows not exposed); nothing in the repo
reads it over REST. Belt-and-suspenders if it ever holds a live key: revoke all on
public.app_config from anon, authenticated (cron runs as postgres — unaffected), and
create a migration for the table so it stops being invisible to the parity check.
- This fix will crash Railway (`zesty-delight`) on next deploy if `API_KEY` is unset in Railway env — confirm it's set there before merging/deploying (see DECISIONS.md S1-1 verification-half note).
## DO-NOT-MERGE-49 — DEFERRED DO NOT MERGE — origin/fix/extract-hallucinated-date-49 (c00c698)
Fully superseded by S2-5c (merged as bb0dcfd). Merging it would delete the
ordinal-date support in _date_appears_in_text and re-break the eviction-summons parse
(the original smoke-test failure). Verified: its extract.py is main's extract.py minus
exactly the ordinal block (13 deletions). Leave the branch as a record; never merge.

## PC-UPL-STALE — DEFERRED fix/pc-upl-stale-tests (71601f4) → Phase B4
Dropped from Phase A (2026-08-15) without resolution. It rewrites test_pc_upl.py to
import get_disclaimer from src/core/upl.py with signature ("standard", "en"),
against src/core/disclaimer.py's ("en", "standard"). Main's UPL surface moved under it
(s3-5c-upl-swallow), so both sides now edit overlapping regions of the same test file.
Resolving it requires choosing the canonical disclaimer source, which is Phase B4's
decision (B4 consolidates on apply_disclaimer across all three known parallel
disclaimer texts). Expect this branch to be rewritten rather than merged once B4 lands.
## B5-UI — RESOLVED (2026-08-30) service date capture (scoped 2026-08-15 from Decision 2; re-scoped 2026-08-30 as the S2-7 UI half)

The ask-the-user half of the B5 pattern. Build root-verified:

- Gap found by inspection: `loadDeadlines` (ResultsPage.jsx) POSTed
  `/api/deadline/analyze` and DISCARDED the response body — the S2-7 gate's
  escalation never reached the UI; users saw "No deadlines detected" while a
  live answer deadline waited on their service date.
- Fix: analyze escalation wired into the Deadlines tab; EscalationBox renders
  the deterministic escalation_reasons with conditional framing ("If you were
  served, enter the date below… if you haven't been served yet, no deadline
  has started to run… don't guess — check the docket") and points at the
  capture form. No LLM text.
- Three-state boundary locked by tests (frontend/src/lib/deadlinesViewState.js
  + .test.js, 11 assertions): 'no-deadlines' is UNREACHABLE whenever
  escalation_reasons is non-empty (wrong-date failure wearing friendlier
  clothes); error state never fabricates; mixed (reasons + rows) renders both.
- Live gate (scripts/live_gate_b5_ui.py, run against prod 2026-08-30):
  Leg A escalation — summons fixture with only an issuance date →
  escalation_needed=True, reasons name 'served' + § 83.60(2), zero rows.
  Leg B supply — service date 2026-08-17 personal → exactly one deadline
  due 2026-08-24 (independently computed 5 business days), trace cites
  § 83.60(2), document_service_facts exactly one row, provenance
  'user_supplied' (B5-f3). ALL LEGS GREEN.
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
## DISC-MISDIAG — RESOLVED CORRECTION (2026-08-15) — the "third parallel disclaimer" was a misdiagnosis
Re-examined during B4b-0 scoping: backend/src/api/routers/deadline.py has NO inline
disclaimer text (verified — no floridalawhelp/floridabar references in the file). The
external links seen in the smoke-test analyze response were apply_disclaimer's OWN text
(src/core/upl.py:37-56) surfacing through deadline.py's apply_disclaimer call. Real
state: TWO parallel disclaimer sources — get_disclaimer (src/core/disclaimer.py:74) and
apply_disclaimer (src/core/upl.py), both carrying external links — plus two agent
prompts that instruct the LLM to print floridalawhelp.org (explainer.py:35,
form_guide.py:23). B4's consolidation target is unchanged (apply_disclaimer canonical);
the "third parallel text" claim in the UPL follow-up above is superseded by this.
## S1-ADJACENT — OPEN model-level external-link emission (found B4b-1a, 2026-08-15)
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
## S2-5-UPL-ERR — OPEN follow-up — deadline router error paths carry NO disclaimer (B4b-2, 2026-08-15)
deadline.py's GET /deadlines and GET /trigger-events except blocks (:62-64, :82-84) and
all HTTPException raises return only {"detail": "..."} — no disclaimer key. Only happy
paths carry one. Pinned by test_deadline_disclaimer.py (error-path absence asserted
deliberately). If error-path disclaimers become required (B4 typed-event goal or UPL
audit), this is the gap. Decision owed: is a bare-error response UPL-acceptable, or
must errors carry the disclaimer too?
## B5-F3 — RECORDED trigger_events.user_* columns deprecated, not dropped (2026-08-16)
document_service_facts (supabase/migrations/20260815000002_b5f3_document_service_facts.sql)
now holds user-supplied service facts; trigger_events.user_service_date,
user_service_method, and service_date_provenance are no longer read or written by
any production code path (src/api/routers/deadline.py, deadline/pipeline.py,
src/memory/db.py — the old get_user_supplied_service_date/set_user_supplied_service_date
methods are kept, unused, marked DEPRECATED). The columns themselves were left in
place intentionally — dropping them is Phase G's job, and should happen alongside
confirming nothing else (dashboards, ad-hoc queries) still reads them.
## B5-F4 — OPEN follow-up — extraction returned the hearing event duplicated (2026-08-16)
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
## OSCA — OPEN form-hosting authorization — follow-up due (2026-08-17, compliance)
The Aug 8 request to OSCA (officially asking about authorization for hosting FL
court forms) has had no response, and a follow-up is due. This is a COMPLIANCE
question about hosting court forms — not an admin chore. The request record
lives in docs/OSCA_CONTACT.md. (Related thread: Susan Emmanuel, OSCA Director
of Communications, separately confirmed on 2026-08-11 that court forms are
public documents — see memory notes; the follow-up here covers the unanswered
Aug 8 email as documented.)
## REQUIRE-DOC — RECORDED _require_document guard — low-priority refactor idea (2026-08-17)
VPS branch refactor/2026-08-15 (commit 6e4f3f7) extracted a duplicated 503/404
doc+session guard from two deadline.py endpoints into _require_document, with
ruff fixes (I001, UP045, F401). The branch is being deleted in the night-run
closeout; this commit was NOT merged. deadline.py has since been heavily
rewritten (B5 series), so this should be a fresh pass if ever picked up — not a
cherry-pick. Low priority, pure refactor, no behavior change.
## SERVICE-KEY — OPEN service_role key exposure + rotation (2026-08-17, security; re-confirmed 2026-08-27 — railway variables dump echoed secrets)
The Supabase service_role key (plus Supabase URL and Management-API tokens) was
found stored in plaintext under GitHub Actions REPOSITORY VARIABLES — visible
unredacted via the UI and `gh variable list` — under names that did not match
what the workflows referenced. The old key is treated as compromised; rotation
is in progress. Completion pending Joe's confirmation that the new key is live
in Railway and in the GitHub Repository secrets. The stale Variables still
exist in the repo Variables store — delete them once rotation is confirmed.
## S1-8 — OPEN settings.API_KEY ships in the frontend bundle (2026-08-17, security + cost)
The frontend embeds API_KEY as VITE_API_KEY and sends it as x-api-key; the SPA
bundle is public, so the key is public by definition. Every API-key-gated route —
including every LLM-calling one — is invocable by anyone who reads the bundle.
Rotating the key does NOT fix this: a public SPA cannot hold a secret. Higher
severity than the original auth-sweep items. Mitigations scoped 2026-08-17 for
Joe's pick: (1) Anthropic spend caps/alerts (account-side backstop), (2) per-IP
rate limits (slowapi exists; wired to 3 of ~13 LLM surfaces), (3) short-lived
server-issued session tokens (proper fix; largest surface).
CORRECTION to the auth sweep framing: gating behind API_KEY raises the bar
against scanners; it is NOT access control.
Related: GitHub-secret pastes routinely carry trailing newlines (SUPABASE_URL
did — parity CI failed with http.client.InvalidURL until parity_check.py and
migrate.yml were hardened to strip whitespace).
CONFIRMED 2026-08-17 — rotation complete: old service_role key revoked at the
Supabase side; new key live in Railway (zesty-delight SUPABASE_SERVICE_KEY) and
in the GitHub Repository secrets — parity CI green on the new key (run
32075188027). Four stale Variables deleted; SUPABASE_URL newline stripped.
Verification sweep: VPS and pop-os backend/.env keys both test valid against
prod post-revocation; Orin manager-surface/.env declares the vars but holds no
values; no hardcoded JWT-shaped key literals anywhere in the repo trees. Note:
backend API_KEY and frontend VITE_API_KEY are a SEPARATE credential from the
Supabase service_role key — never exposed, not rotated.

## S3-6 — RESOLVED police-report case law: generic famous cases (CLOSED 2026-08-27)
Police Report Analyzer returned the same famous murder/generic cases for
every report (retrieval searched only abstract tag names, ranked by global
cite_count). Fixed: fact-term extraction from the LLM's own discrepancy /
missing-field / charge text + relevance ranking (matched DESC, overlap DESC,
cite_count DESC) + junk-row filter + single-anchor ILIKE queries with
advancement on junk-only / below-threshold results (multi-term ORs exceed
the Supabase statement timeout, 57014). Merged at 79fa02f after a green
Phase 3 live gate (5/5 criteria). Before: Caraballo 44 / Tracey 53 /
Lukehart 47. After: Caldwell 52 (Miranda) / Tracey 53 (4A warrant) /
Nieminski 21 (anonymous-tip — on point).

Logged rule (Joe 2026-08-27): case-law results never present a charge class
more severe than the report's own charges. Operational form: homicide cases
are EXCLUDED whenever the report carries no homicide charge — hard,
deterministic, text-based (_CHARGE_HOMICIDE stems). Where exclusion thins
results below the limit, they stay thin; no backfill (gaps degrade to
silence). Non-homicide charge classes are NOT filtered — Caldwell (burglary
felony) stays for a misdemeanor-report user; McWatters (murder narrative)
goes.

Phase J CLOSED 2026-08-27 (Decision 18): pop-os diff showed the branch
strictly older — nothing unique of value (its content = the original
tag-overlap retrieval; a merge would have deleted modern work). Branch
deleted on pop-os (was 3185a47).

## S1-2B — DEFERRED attorney-referral 500s: PAUSED by Decision 19 (2026-08-27)
/api/attorney-referral/intake + /submit 500 in prod (migration 20260813
never applied; tables missing). Joe has no attorneys yet — work paused
until he resumes it. Do not fix, do not deploy, do not chase.

## CORPUS-SYNC — RECORDED Aug 25 cron 784cf1afc5d1 (recorded 2026-08-27, was missing from repo ledger)
Pre-authorized by Joe (Aug 24): statutes 24,364 -> 25,020 (656 inserted, 0 failed, 27 legacy
kept), court_rules 510 -> 785 (traffic 43 + juvenile 207 + svp 25 inserted). Statutes gates
per the sync skill: re-diff missing=0, byte-fidelity 10/10, live spot-check 3/3 vs
leg.state.fl.us — all PASS (cron report at ~/.hermes/cron/output/784cf1afc5d1/; delivered to
Joe via @legalclear_bot). STATUS.md had NOT been regenerated (still showed 24,364/510) — that
gap is the "grew without a report" symptom. Counts now live-verified 2026-08-27: 25,020 / 785.

## S1-2C — RESOLVED VALIDATED + CLOSED (2026-08-30) — 275 rule rows pass Decision 12/14 retro-validation
The Aug 25 load happened without rule-side validation (process gap — confirmed). Retrospective
validation against the OFFICIAL floridabar PDFs (downloaded fresh from the rows' own source_urls:
Traffic 01-01-2026, Juvenile 01-01-2026, SVP 01-01-2024) PASSES:
- Load fidelity: 275/275 DB rows byte-identical to the Orin stage source — nothing mangled in transit.
- Body detection: 0 empty rows. 3 rows <120 chars — all GENUINELY short rules (8.715 GAL=112,
  8.800 applicability=118, 8.850 applicability=110; official text is 126/132/123 chars). No stubs.
- Ratio sampling (10% per set = 29 rows + the 6 FORM rows): svp 4/4 ratio 1.0, traffic 4/4 ratio 1.0,
  juvenile 21 rows 0.966-1.0 — every sub-1.0 delta traced to extraction artifacts (pdftotext page
  footers "January 1, 2026 Florida Rules of Juvenile Procedure" interleaved mid-text, "Page N of 469"
  markers, TOC-vs-body windows), spot-checks word-for-word identical. 6 rows flagged "missing" are
  FORMS (FORM 8.901/8.909/8.913/8.951/8.976/8.977) — all verified present in the official PDF.
  ZERO content failures; NO rows replaced; no prod writes needed.
- Recorded gap fixed for the future: legalclear-fl-corpus-sync skill now includes rule-side
  fidelity gates (official-PDF ratio sampling) in Phase 3, so the next sync cannot skip them.