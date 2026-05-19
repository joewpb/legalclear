# LegalClear — Build Plan (FINAL)

This supersedes all earlier plan files. Nine phases. Every decision from planning
is locked. Hand Claude Code ONE phase at a time; verify each Definition of Done
before the next. Do not one-shot this plan.

Recommended placement: `phases/BUILD_PLAN.md`.

## Confirmed project facts
- Backend: Python. Frontend: JS/TS. Mobile: Expo/React Native.
- Database: Supabase Postgres 17, project `miedifclpqewnixxkahs` (us-west-2).
- Hosting: Railway. `SUPABASE_URL` points at the project above.
- Architecture: backend-only. The client talks only to the Railway backend; the
  backend is the only thing that talks to Supabase and holds the service-role key.
- Live tables: `users`, `sessions`, `documents`, `chat_messages`,
  `usage_stats`, `push_tokens`, `packets`.

## Confirmed scope decisions
- Forms use a **version-aware permanent cache**: every form is stored permanently
  in a LegalClear bucket and served from the bucket. A lightweight periodic
  change-detection check re-pulls a form ONLY when it has actually changed. The
  rule is "re-pull only when changed," never "never check."
- Expungement is OUT of v2. Criminal/expungement documents route to escalation.
- Florida statutes, court rules, and local administrative orders corpus is IN.
- Cost-per-document instrumentation is IN.
- Multilingual: architecture is language-parameterized now; English at v2 launch,
  Spanish in v2.1 as a fast-follow.
- `risk_scan`: CUT from v2. The `documents.risk_scan` column stays unused.
- Business liability (ToS, disclaimer enforceability, E&O insurance, operating
  entity): a parallel NON-engineering workstream owned by Joe with his attorneys
  and an insurance broker. It gates public launch, not the build. Its only build
  touchpoint: the Phase 8 disclaimer must be drafted consistently with the ToS.

## Core Principles — apply to every phase
1. The product produces **legal information**, never **legal advice**. It
   translates, surfaces options, explains consequences. It never selects a course
   of action for the user.
2. **LLMs extract. Deterministic code computes.** No model does date arithmetic.
3. Every deadline carries a full `computation_trace` with rule citations.
4. No "done" claim without fresh test/verification evidence.
5. "Unknown" is a valid, first-class output. A confident wrong answer is a liability.
6. **Backend is the security boundary.** The backend uses the service-role key,
   which bypasses RLS. Every backend query reading user data must be explicitly
   scoped to the authenticated user. RLS is the second line of defense.
7. **Language-parameterized from day one.** Every user-facing output accepts a
   language parameter. English ships first; Spanish must not require re-architecture.
8. **Respect source robots.txt and terms.** `flcourts.gov` and its file CDN
   disallow automated crawling. The plan never bulk-crawls them. Form acquisition
   is a one-time human/browser-assisted harvest plus a lightweight change-detection
   check, ideally backed by an explicit access arrangement with the Office of the
   State Courts Administrator (OSCA).
9. **A served form is never knowingly stale.** A form whose change-detection
   status is unresolved is gated, not served silently.

---

## PHASE 0 — Stabilize the Foundation

**Objective:** Eliminate ambiguity and clutter. No new features.

**Status note:** Already complete — repo private, secrets rotated, full git
history scanned clean, duplicate Supabase project deleted. Below is what REMAINS.

### Tasks
1. Resolve the 3 open pull requests. Merge what is good, close what is stale.
2. Clean the repository root: remove/relocate `files (Copy 1)/`, `files.zip`,
   `doc.txt`, `dummy.pdf`. Update `.gitignore`.
3. Audit the one-shot prompt files (`Complete One Shot Build.md`,
   `LegalClear_OneShot_Prompt.md`) against the Core Principles. Update or archive
   any that conflict.
4. Reconcile `CLAUDE.md` / `AGENTS.md` with reality: real repo structure, build
   and test commands, confirmed project facts, the nine Core Principles near the top.
5. Document the baseline in the README.

### Definition of Done
- Zero open PRs, or each remaining one has a documented reason.
- Repo root contains only source, config, documentation.
- One-shot prompt files confirmed consistent with Core Principles.
- `CLAUDE.md`/`AGENTS.md` matches reality and states the Core Principles.

### Guardrails
- Do not force-push to `main`. Do not change application logic in this phase.

---

## PHASE 1 — Database Schema, Security & PII

**Objective:** Add tables later phases require; fix `packets`; write the RLS
policy set; implement retention and PII minimization; add cost instrumentation.

**Preconditions:** Phase 0 complete.

### Use a Supabase development branch
Apply and test all migrations on a development branch first. Merge to production
only after verification. Production holds live data — migrations are non-destructive.

### Task 1 — New tables

```sql
create table public.court_forms (
  id                     uuid primary key default gen_random_uuid(),
  form_number            text not null unique,   -- "12.901(a)"
  title                  text not null,
  category               text not null,          -- family_law | civil | etc.
  court_revision_date    text,                    -- revision stamped on the form
  content_id             text,                    -- court's stable content ID
  source_download_url    text,                    -- court URL for change-checks/re-pull
  source_page_url        text,                    -- human-facing court page
  situation_tags         text[],                  -- maps user situations to forms
  storage_path           text,                    -- permanent copy in Supabase Storage
  content_hash           text,                    -- sha256 of the stored file
  last_checked_at        timestamptz,             -- when change-detection last ran
  last_changed_at        timestamptz,             -- when the form last actually changed
  status                 text not null default 'unverified',
                                                  -- active|stale|withdrawn|unverified
  plain_language_summary text,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create table public.trigger_events (
  id               uuid primary key default gen_random_uuid(),
  document_id      uuid references public.documents(id) on delete cascade,
  event_type       text not null,          -- served | filed | issued | rendered
  event_date       date not null,
  service_method   text not null,          -- personal|mail|e_service|publication|unknown
  document_type    text not null,
  jurisdiction     text not null default 'FL',
  circuit          int,
  county           text,
  case_number      text,
  raw_text_excerpt text not null,
  confidence       numeric not null,
  created_at       timestamptz not null default now()
);

create table public.deadlines (
  id                     uuid primary key default gen_random_uuid(),
  document_id            uuid references public.documents(id) on delete cascade,
  trigger_event_id       uuid references public.trigger_events(id) on delete cascade,
  label                  text not null,
  due_date               date not null,
  governing_rule         text not null,
  consequence_if_missed  text not null,
  severity               text not null,    -- fatal | high | medium | low
  confidence             numeric not null,
  escalation_recommended boolean not null default false,
  computation_trace      jsonb not null,
  reminder_state         text not null default 'pending',
  created_at             timestamptz not null default now()
);
```

### Task 2 — Fix the `packets` table
Migrate `id` and `user_id` from `text` to `uuid` (generate UUIDs for the 31
existing rows; add a `user_id` foreign key to `users.id`, nulling values that do
not resolve). Migrate `created_at`, `filed_at`, `paid_at` from `text` to
`timestamptz`. Include a backfill; the migration must be reversible; all 31 rows
must survive.

### Task 3 — Cost instrumentation
Add to `usage_stats`: `total_input_tokens int`, `total_output_tokens int`,
`estimated_cost_usd numeric`. Every phase making an LLM call writes these.

### Task 4 — Row Level Security policies
All tables have RLS enabled but ZERO policies. Write restrictive policies:
`users` → `auth.uid() = id`; `sessions` → `user_id = auth.uid()`; `documents`,
`trigger_events`, `deadlines`, `chat_messages` → scoped through the session join;
`push_tokens`, `packets` → `user_id = auth.uid()`; `usage_stats` → service role
only; `court_forms` → authenticated read of `status = 'active'` rows, writes
service-role only.

Reference join-based policy:

```sql
create policy "users_access_own_documents" on public.documents
  for all to authenticated
  using ( session_id in (
    select id from public.sessions where user_id = auth.uid()
  ));
```

### Task 5 — Retention and PII minimization
- Raw `documents.document_text`: purge 30 days after upload on a fixed clock; a
  login does NOT reset it.
- Structured outputs (jsonb columns): retained while the account is active.
- Guest documents: purge within 72 hours.
- Enforce with `pg_cron`. Add an on-demand document delete endpoint.
- After extraction, run a PII redaction pass over retained `document_text`
  removing SSNs, full dates of birth, and financial account numbers (Presidio).

### Task 6 — Guest / anonymous handling
Implement Supabase anonymous sign-in: a guest gets a real `auth.uid()`, the RLS
policies apply automatically, and the account converts to permanent on sign-up,
carrying the guest's document over. Rate-limit anonymous uploads per IP/device.

### Task 7 — Regenerate types
Regenerate TypeScript types for the frontend AND the Expo mobile app, and Python
models for the backend.

### Definition of Done
- `court_forms`, `trigger_events`, `deadlines` exist with RLS policies.
- `packets` uses `uuid`/`timestamptz`, has a `user_id` FK, all 31 rows survived.
- Every table has a verified restrictive RLS policy.
- `pg_cron` retention job runs; raw text purges on a fixed 30-day clock.
- On-demand delete endpoint exists; PII redaction runs after extraction.
- Anonymous sign-in works; guest documents convert on sign-up.
- `usage_stats` has cost columns; types regenerated for all three clients.
- All migrations verified on a branch before production merge.

### Guardrails
- Never run untested migrations against production. Do not drop/truncate any
  table. Do not delete `packets` rows. Do not weaken RLS for convenience.

---

## PHASE 2 — Form Catalog & Version-Aware Permanent Cache

**Objective:** Serve court forms to users from a LegalClear-controlled bucket,
fast and court-outage-proof, while guaranteeing a served form is never knowingly
stale.

**Preconditions:** Phase 1 complete (`court_forms` exists).

### Model: permanent cache + change detection
Every form is stored permanently in a LegalClear bucket (Supabase Storage) and
served from the bucket — the normal download path never touches the court's
server. A lightweight periodic change-detection job is the ONLY thing that
contacts the court, and it re-pulls a form only when that form has actually
changed. The rule is "re-pull only when changed," never "never check."

### Task 1 — Build the catalog and harvest into the bucket
Seed `court_forms` from `florida-family-law-forms-seed.csv` (12 verified forms +
the 39 family-law form-group catalog). Complete the family-law catalog and
download every form into the bucket via a one-time human or browser-assisted
pass through the official court form pages — a person using a browser, not an
automated crawler, and not a robots.txt violation. For each form record
`storage_path`, `content_hash`, `content_id`, `source_download_url`,
`court_revision_date`, `situation_tags`, and set `status = 'active'`.

### Task 2 — Download endpoint
A backend endpoint that, given a `form_number`, streams the form from the bucket
through the LegalClear domain. The normal download path does not contact the
court. It refuses to serve any form whose `status` is not `active`.

### Task 3 — Change-detection job
A lightweight periodic job (weekly) that, for each form, checks whether the
court's published `court_revision_date` or file hash has changed. If unchanged:
update `last_checked_at`, keep serving the bucket copy. If changed: re-pull that
ONE form, update `storage_path`/`content_hash`/`last_changed_at`, and flag it for
review. Also monitor the Florida Supreme Court rules-amendment announcements as a
human-facing change signal, so detection does not depend solely on polling.

### Task 4 — OSCA access arrangement
Joe contacts the Office of the State Courts Administrator to establish explicit
permission for hosting the approved forms and for the change-detection checks.
This is the durable de-risking of the whole phase and the path for civil,
probate, and small claims forms, which are less centralized.

### Task 5 — Stale / withdrawn handling
If change detection flags a form changed-but-not-yet-reviewed, or a form is
withdrawn, set `status` to `stale` or `withdrawn`. The download endpoint then
shows a notice and a link to the court's forms page instead of serving the old
copy. A redirect on a known-stale form is correct; serving it silently is not.

### Definition of Done
- The family-law catalog is fully populated; every form is stored in the bucket.
- The download endpoint serves from the bucket through the LegalClear domain and
  refuses non-`active` forms.
- The change-detection job runs, re-pulls only changed forms, and updates status.
- The OSCA contact has been initiated (a sent request, at minimum).
- The stale/withdrawn handling is implemented and tested.

### Guardrails
- Do not bulk-crawl `flcourts.gov` or its CDN; respect their robots.txt. The only
  court contact is the change-detection job and one-time/human harvest.
- "Re-pull only when changed" — never "never check." The change-detection job is
  not optional.
- Never serve a form whose `status` is not `active`.

---

## PHASE 3 — Statutes, Court Rules & Local Administrative Orders Corpus

**Objective:** Ingest Florida statutes, the procedural rule sets, and per-circuit
local administrative orders, so the `explanation` feature is grounded in law and
the deadline engine can account for local rules and court closures.

**Preconditions:** Phase 1 complete.

### Tasks
1. **Verified law source registry.** Florida Statutes (Florida Legislature,
   `leg.state.fl.us`, bulk XML); procedural rule sets on `flcourts.gov` (Civil
   Procedure, Family Law Rules, Small Claims, Probate, General Practice and
   Judicial Administration, Appellate Procedure). Use the `verified`/`VERIFY`
   discipline; never automatically crawl a robots-disallowed path.
2. **`statutes` and `court_rules` tables.** Store official text verbatim, with
   citation, chapter/section/rule numbers, and effective dates.
3. **Ingest** Florida Statutes and the procedural rule sets.
4. **Local Administrative Orders workstream.** Create `local_administrative_orders`
   (circuit, AO number, subject, effective date, text/summary, source) and
   `court_closures` (circuit, county, closure_date, reason, source). Each Florida
   circuit publishes its own administrative orders — there is no clean statewide
   feed, so this is partly manual and partly covered by the OSCA conversation.
   Start with the circuits LegalClear serves first (the 19th Circuit covers the
   Stuart area); expand outward.
5. **Queryable by citation.** Exact-citation lookup is the requirement;
   embeddings (pgvector) are an optional enhancement.
6. **Refresh cadence.** Statutes refresh annually after the legislative session.
   Local AOs and closures refresh on each circuit's publication cadence.

### Definition of Done
- `statutes`, `court_rules`, `local_administrative_orders`, `court_closures`
  exist and are populated for at least the priority circuits.
- All are queryable by citation / by circuit.
- The law source registry is fully `verified`.
- Refresh cadences are scheduled or documented.

### Guardrails
- Store official statute, rule, and AO text verbatim. Paraphrasing happens only
  at the user-facing explanation layer, clearly labeled as plain-language.
- Every record cites its source.
- Where local AO or closure data for a circuit is missing, mark it explicitly so
  the deadline engine can escalate rather than assume.

---

## PHASE 4 — The Deadline Engine

**Objective:** Extract deadline-triggering events from a document, compute
deadlines deterministically under Florida rules, write to `trigger_events` and
`deadlines`.

**Preconditions:** Phase 1 complete; Phase 3 complete (`court_closures`).

### Architecture: two stages, strictly separated
- Stage 1 (LLM): extract trigger events — dates, service methods, document types.
  Does NOT compute deadlines.
- Stage 2 (deterministic code): compute deadline dates from extracted events
  using a hard-coded Florida rule library. No LLM.

### Tasks
1. **Florida rule library** (`backend/deadline/rules.py`): document type ->
   response period, governing rule citation, severity, plain-language
   consequence. Cover civil summons (20 days, Fla. R. Civ. P. 1.140(a));
   residential eviction (5 business days, Fla. Stat. 83.60(2)); foreclosure
   complaint (20 days); family law petition (20 days, Fla. Fam. L. R. P. 12.140);
   small claims (pretrial conference date); notice of appeal (30 days, Fla. R.
   App. P. 9.110(b)); motion for rehearing (15 days); discovery requests (30
   days). Include a statewide Florida holiday calendar. Versioned data; each rule
   cites its source.
2. **Deterministic computation engine** (`backend/deadline/compute.py`):
   implement Fla. R. Jud. Admin. 2.514 — exclude the trigger day; periods under
   7 days and explicitly business-day periods exclude weekends and holidays,
   periods of 7+ days count calendar days; roll a weekend/holiday endpoint
   forward to the next business day; mail service adds 5 days, e-service adds
   nothing. **Consult BOTH the statewide holiday calendar AND the `court_closures`
   table for the specific court** the case sits in. Produce an ordered
   `computation_trace` with rule citations for every deadline.
3. **Trigger-event extractor** (`backend/deadline/extract.py`): an LLM call
   returning schema-validated trigger events. Extract only explicitly stated
   facts; never infer or compute dates; mark `unknown` when unclear. Reject
   schema-invalid output; retry once; then escalate.
4. **Wire the pipeline**: extract -> `trigger_events` -> compute -> `deadlines`.
   Set `escalation_recommended = true` when severity is `fatal` and confidence is
   below 0.90.
5. **Failure modes**: missing service date -> escalate. Ambiguous document type
   -> compute both, treat the earlier deadline as binding, disclose. Service
   method unclear -> use the shorter deadline, disclose the assumption. Deadline
   already past -> high-severity flag. Missing local closure data near a fatal
   deadline -> escalate; do not assume the court was open.

### Definition of Done
- The pipeline produces `trigger_events` and `deadlines` rows.
- Every `deadline` has a complete, human-readable `computation_trace`.
- The engine consults statewide holidays AND per-court closures.
- Date arithmetic lives entirely in deterministic code.
- All failure modes are handled and covered by tests.

### Guardrails
- The LLM must never compute or output a deadline date — extraction only.
- Never silently default an unknown field; disclose or escalate.
- Do not ship a deadline rule without a source citation.

---

## PHASE 5 — The Document Triage Classifier

**Objective:** Classify each uploaded document so it routes to the correct
deadline rules and the correct catalog forms; route criminal/expungement to
escalation.

**Preconditions:** Phase 4 complete.

### Tasks
1. Build the classifier (`backend/triage/classify.py`): identify document type
   (civil summons, eviction summons, foreclosure complaint, family petition,
   small claims summons, motion, order, judgment, notice of hearing, discovery
   request, criminal, unknown) and jurisdiction.
2. Write output to `documents.classification` with per-field confidence.
3. Route on classification: select the deadline rules Phase 4 applies and the
   `court_forms` catalog entries surfaced as relevant.
4. Route criminal and expungement documents straight to escalation — no standard
   analysis.
5. Low confidence -> mark for human review; let the user confirm or correct the
   type via a dropdown.

### Definition of Done
- Every processed document has a populated `documents.classification`.
- Classification drives deadline-rule selection and form selection.
- Criminal/expungement documents route to escalation.
- Low-confidence classifications route to user confirmation.

### Guardrails
- A low-confidence classification must not silently drive a deadline computation.
- `unknown` is a valid classification and must be handled gracefully.

---

## PHASE 6 — The Reminder & Notification Scheduler

**Objective:** Deliver deadline reminders. The deadline engine's value is
realized only when a user is actually reminded before the deadline.

**Preconditions:** Phase 4 complete (`deadlines`); Phase 1 complete (`push_tokens`).

### Tasks
1. **Reminder schedule logic.** For each deadline, schedule reminders before
   `due_date` — e.g. 14, 7, 3, 1 days out — scaled to severity and to how much
   time remains. A deadline only 4 days away gets a compressed schedule.
2. **Delivery.** Send via Expo push using `push_tokens` / `users.expo_push_token`.
   Provide an email fallback for users without a push token.
3. **Scheduler mechanism.** A `pg_cron` job (or scheduled function) checks for
   due reminders and fires them. Update `deadlines.reminder_state`
   (`pending` -> `scheduled` -> `sent` -> `expired`).
4. **Respect language.** Notification copy uses the user's `preferred_language`.
5. **Edge cases.** A past deadline gets no "you still have time" reminder — it
   gets `expired`. A deadline within hours gets an urgent reminder. Respect user
   notification preferences.

### Definition of Done
- Reminders fire ahead of deadlines on a sensible schedule.
- `reminder_state` is tracked accurately per deadline.
- No reminder implies time remains on an expired deadline.
- Email fallback works for users without a push token.

### Guardrails
- Never send a reminder implying time remains when the deadline has passed.
- Respect user notification preferences and language.

---

## PHASE 7 — The Evaluation Harness

**Objective:** Prove the deadline engine and classifier are correct against a
ground-truth test set. No feature ships on intuition.

**Preconditions:** Phases 4 and 5 complete.

### Tasks
1. **Assemble a 50-document evaluation set** (`backend/evals/`). Cover civil
   summonses, residential eviction summonses, family law petitions, small claims
   summonses, motions, orders/judgments, notices of hearing, and adversarial
   edge cases (service by publication, dates near month/year boundaries). Redact
   party names from any real documents.
2. **Hand-compute the ground truth** for each: correct document type, trigger
   date, service method, final deadline date. Lock these answers.
3. **Build the eval runner** (`python -m evals.run_all`). Report precision and
   recall for document type classification, trigger date extraction, service
   method extraction, and final deadline date (exact match).
4. **Set the launch gate.** The system must reach 100% accuracy on the final
   deadline date for all `fatal`-severity documents before any deadline feature
   is shown to real users. If 100% is not reached, narrow the supported document
   types until it is.
5. **Wire the eval into CI.** No change to the deadline engine or classifier
   merges to `main` without the full eval passing.

### Definition of Done
- A 50-document eval set with locked ground truth exists in the repo.
- `python -m evals.run_all` produces a precision/recall report.
- The `fatal`-tier deadline accuracy gate is met, or supported scope is narrowed
  to meet it.
- CI runs the eval on every relevant PR.

### Guardrails
- Never edit a ground-truth answer to make a test pass. Fix the code.
- Do not claim the eval passes without attaching the fresh run output.

---

## PHASE 8 — UPL Wall & Escalation Enforcement

**Objective:** Ensure every user-facing output is legal information, not legal
advice, and that high-stakes situations route the user toward professional help.

**Preconditions:** Phases 4, 5, 6, 7 complete.

### Tasks
1. **Audit every output path.** Review content produced for
   `documents.explanation`, `form_guide`, `escalation`, deadline output, and chat
   responses. Every output must translate, surface options, and explain
   consequences — never instruct the user which option to choose.
2. **Implement escalation triggers.** Recommend a limited-scope attorney
   consultation when: severity is `fatal` and extraction confidence is below
   0.90; a deadline is within 72 hours; document type is `unknown`; the matter
   involves minor children; or the document is criminal or expungement-related.
   Write results to `documents.escalation`.
3. **Implement the disclaimer layer.** Every analysis carries a clear, persistent
   statement that the output is legal information, not legal advice. Draft it
   consistently with the Terms of Service.
4. **Form provenance display.** Every form shown displays that it is the official
   court form, with its `court_revision_date` and `last_changed_at`. A form whose
   `status` is not `active` is not served (handled in Phase 2).
5. **Documented attorney review.** Put ACTUAL generated outputs — the real text
   of `explanation`, `form_guide`, `escalation`, and deadline output — in front
   of the Florida attorneys reviewing the product. Have them mark specific
   wording against the UPL line. Keep the review documented in writing.
6. **Fallback path.** When the system cannot safely analyze a document (failed
   extraction, unknown type, conflicting data), it says so plainly and directs
   the user to appropriate help rather than producing a low-confidence answer.

### Definition of Done
- No user-facing output instructs the user which legal action to take.
- Escalation triggers fire correctly and are covered by tests.
- A disclaimer is present on every analysis.
- Forms display provenance and revision information.
- A documented attorney review of real generated outputs is on file.

### Guardrails
- Do not weaken or remove the disclaimer layer for UX reasons.
- Do not serve a stale or withdrawn form.
- When in doubt, the system escalates or declines — it does not guess.

---

## Sequencing Summary

| Phase | Deliverable | Gate before next phase |
|-------|-------------|------------------------|
| 0 | Clean repo, accurate agent docs, audited prompts | Zero unexplained PRs |
| 1 | Schema + RLS + retention + PII + cost instrumentation | Migrations verified on a branch |
| 2 | Form catalog + version-aware permanent cache | Bucket populated; change-detection runs |
| 3 | Statutes, rules, local AOs & closures corpus | Tables populated for priority circuits |
| 4 | Deadline engine (extract + compute) | Every deadline has a trace |
| 5 | Document triage classifier | Classification drives routing; criminal escalates |
| 6 | Reminder & notification scheduler | Reminders fire; no expired-deadline reminders |
| 7 | Evaluation harness | 100% on `fatal`-tier deadline accuracy |
| 8 | UPL wall + escalation + attorney review | No output gives legal advice |

**Run one phase per Claude Code session. Verify the Definition of Done before
moving on.**

## Parallel Workstream — Not Engineering, But Gates Launch

The business liability layer — operating entity (LLC/corp), Terms of Service,
disclaimer enforceability, and tech E&O insurance — runs alongside Phases 0-8 and
is owned by Joe with his attorneys and an insurance broker. It does not block the
build. It must be resolved before public launch. Its only build touchpoint: the
Phase 8 disclaimer is drafted consistently with the Terms of Service.
