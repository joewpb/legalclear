# REMEDIATION_PLAN.md
### LegalClear — post-audit remediation, phased.
**Written:** 2026-08-14 · **Owner:** Joe · **Executor:** Hermes
**Current state:** Phases A–H COMPLETE (2026-08-17) · origin/main tracked live in STATUS.md (see repo root — the sync ledger; this header updated 2026-08-20, last known main a9cb141)
G1, G2, G3, G4, G5 CLOSED · Phase I scoped 2026-08-20 (9 slices, I-1 first), awaiting build

---

## How this document works

Hermes executes a **whole phase** and reports once at the end, escalating only on the
triggers in §2. Joe reviews per phase, not per item. Anything not on the escalation list
is Hermes's call, made by the standing rules in §1.

The plan is a hypothesis. When a finding contradicts it, the finding wins — escalate and
the plan gets amended. Do not improvise around a contradiction.

---

## 1. Standing decision rules — Hermes decides these without asking

| Situation | Rule |
|---|---|
| Item touches more than one surface (backend + frontend + new test) | Split into separate dispatches. Never one run |
| Run exhausts turns | Continuation pattern: name what is done, forbid redoing it, one job, 25 turns. **Never raise budget to fix a turn problem** |
| Two consecutive exhaustions | Halt the phase. Question dispatch sizing first, the repo second |
| A run reports it wrote a file | Verify the artifact exists. Child summaries are self-reports; artifacts are evidence |
| A run stops rather than shipping a break | That is success. Log its finding, move on. Do not push it to code around the obstacle |
| A run finds a new defect | Log to FOLLOW_UPS.md with a severity tier. Do not fix it, do not ask |
| Test suite disagrees with a run's report | Suite wins. Flag the discrepancy |
| Item is blocked by a dependency in this plan | Skip it, note it, continue the phase |
| Turn caps | 40 single-surface · 60 multi-surface · 50 read-heavy diagnose · 25 continuation |
| Budget | $3 sonnet · $6 fable. Budget has never been the binding constraint |

**Never, under any instruction:** merge to main, push a `fix/*` branch, apply a migration,
run DDL, print or transmit a secret value, delete anything, or deploy — unless a phase
grants that authority explicitly and for that phase only.

---

## 2. Escalation triggers — only these reach Joe mid-phase

1. A **legal-correctness** question (which date anchors a rule, what a disclaimer must say)
2. Prod **DDL or migration** required
3. A **secret** value is needed
4. A finding **contradicts this plan**
5. Two consecutive turn exhaustions
6. Anything touching **auth, tenancy, or RLS** that looks ambiguous rather than mechanical

Everything else waits for the phase report.

---

## 3. Gates — hard preconditions, not preferences

| Gate | Condition | Blocks |
|---|---|---|
| **G1 — Real users** | S2-7 resolved AND UPL wall consolidated | Pointing the deadline pipeline at anyone but a supervised tester |
| **G2 — Payments** | `filings` verified working AND S1-3 email verification built | Flipping `PAYMENTS_ENABLED` on |
| **G3 — Manual DDL** | ✅ CLOSED 2026-08-17 (CI migrations live: Management-API PAT workflow, schema_migrations tracking, parity OK) | Any further hand-applied migration |
| **G4 — Referral path** | S1-5 decided AND referral RLS written | Applying the 20260813 migration; scheduling S1-3b |

G1 is the one that matters. A wrong eviction deadline is a default judgment.

---

## PHASE A — Land the work already done · ✅ COMPLETE 2026-08-14

**Final SHA:** 6178604 (code) → d042e06 (docs) · **Suite:** 237/1 from a 200/1 baseline
**Rollback point:** b82e68b

- 11 fix branches squash-merged, each verified (suite + deploy) before the next
- `ENVIRONMENT` flipped `development` → `production`; S3-3 startup validator active and
  passing. S1-7 inert-validator risk closed
- Reminder plumbing live end to end: cron fired 03:00 UTC, authenticated via the corrected
  `app_config` key, scheduled two reminders (3d + 1d) for the Aug 21 eviction deadline
- `parity_check.py` runs from main, reporting exactly the expected drift
- Applied manually via SQL editor: `app_config` revoke + key update, `filings` migration
  (20260704), cron amendment reading `app_config` instead of dead GUCs
- Closure seed (99 rows, circuits 1–20) applied 2026-08-14; table complete at 108 rows

**Deferrals carried forward:**
- `fix/pc-upl-stale-tests` (71601f4) → **Phase B4**. Its conflict requires deciding whether
  `src/core/disclaimer.py` or `src/core/upl.py` is canonical — a B4 decision, not a test merge
- Three merged-branch deletions → skipped, harmless, Joe's cleanup
- `origin/fix/extract-hallucinated-date-49` (c00c698) → **DO NOT MERGE**. Fully superseded
  by S2-5c; merging would delete ordinal-date support and re-break the summons parse

---

## PHASE B — Correctness blockers (G1) · ✅ B1–B4 COMPLETE 2026-08-15
**Final B-phase SHA:** 3a1607e (+ docs e6e0bb9) · Suite 275/1 from a 249/1 baseline.

- B1 (S2-7 anchors) — merged 2826fbd: rules declare required_anchors; extractor labels
  date kinds; wrong-kind date skips + escalates, never substitutes.
- B2 (S3-5d) — merged bd6e0e7: insert failures escalate, counters honest.
- B3 (S3-5e) — merged e6df4b8: every rejected date logged with value + span.
- B4 (UPL consolidation) — merged 3a1607e: apply_disclaimer canonical v2 (Decision 3),
  links stripped, get_disclaimer delegates; typed `event: disclaimer` on success AND
  error paths across forms/criminal/discovery/wills_trusts/small_claims;
  attorney_referral wrapped (was bare); intake migrated; frontend SSE tolerance
  (b4a, d5816ef) shipped first. fix/pc-upl-stale-tests SUPERSEDED (rewritten as b4c,
  not merged — its version no longer imports).
- B4d (URL output filter, Decision 4) — ADDED SCOPE, dispatched 2026-08-15.
- B4e (streaming error-path disclaimers conditional on content, Decision 5) — ADDED
  SCOPE, dispatched 2026-08-15.

**G1 REMAINS CLOSED** — B5 (service-date capture per Decision 2) has not shipped.

**Goal:** the pipeline becomes safe to point at a real tenant. **This is the critical path.**

### B1 — S2-7, date anchors. Diagnose first. fable, 50 turns, $6.
Three questions, answered with file:line before any code:
- Does the extractor distinguish **issuance / service / hearing** dates, or treat any date
  as interchangeable?
- Does each deadline rule **declare** which anchor it requires?
- What happens when the required anchor is absent?

Then fix: rules declare their anchor; extractor labels date types; **absent anchor →
skip and escalate, never substitute.**

**Escalate, do not decide:** service of process is usually proven by a separate return-of-
service document and is often not extractable from the summons at all. If so, the correct
product behavior is to *ask the user when they were served* rather than guess — that is a
product decision with legal consequences and belongs to Joe.

### B2 — S3-5d, pipeline insert swallows. sonnet, 40 turns.
`pipeline.py:209,245` swallow DB insert errors behind a 200. Fix before further pipeline
work — it is what made "never called" indistinguishable from "called and failed silently."

### B3 — S3-5e, verifier silence. sonnet, 40 turns.
`_date_appears_in_text` nulls rejected dates without logging. Log every rejection with the
extracted value and surrounding text span. You will not enumerate your way out of legal
date phrasing; make the misses visible instead.

### B4 — UPL consolidation. Diagnose, then fix.
Three parallel disclaimer texts known: `get_disclaimer`, `apply_disclaimer`, and
`deadline.py`'s inline text (which carries **external links**, violating the
no-external-links rule).

> CORRECTION (2026-08-15, B4b-0 scoping): deadline.py has NO inline text — the links
> were apply_disclaimer's own text surfacing through it. Real state: TWO sources
> (get_disclaimer, apply_disclaimer), both with external links, plus two agent prompts
> instructing the LLM to print floridalawhelp.org (explainer.py:35, form_guide.py:23).
> Consolidation target unchanged: apply_disclaimer canonical.

- **First decision: which source is canonical.** Recommendation is `apply_disclaimer`.
  This unblocks `fix/pc-upl-stale-tests`, deferred from Phase A
- Single source, versioned, imported by every path
- Typed SSE event, not appended text. Emit on **success and error paths**
- **Deploy order: client tolerance ships first.** The client parser cannot currently
  tolerate unknown event types — backend-first would make the disclaimer vanish from the
  UI, a UPL regression worse than status quo
- Covers Criminal and Discovery streaming success paths, and the attorney-referral router

**Exit:** G1 opens. Escalate to Joe before declaring it.

---

## PHASE C — Finish the reminder feature · ✅ COMPLETE 2026-08-16 (C-1 df7973c, C-2 d4fda09; cron chain proven live; pg_cron job-level check = Joe's SQL editor)
**Depends on:** Phase A. **Independent of B.**

- **C1 — DONE.** Cron fires, authenticates, schedules. Two reminders live for Aug 21
- C2 — Email delivery is an honest stub; reminders will terminate `failed` on Aug 18.
  Build real delivery. **Escalate the provider choice** — Joe's call, not a dispatch
- C3 — Phase 2/3 cron jobs carry the identical dead-GUC read. Same treatment.
  **DDL → escalate for manual paste until G3**
- C4 — `push_tokens` endpoint serves a mobile app that is an empty directory. Log as a
  decision Joe owes: build, or remove the endpoint in Phase G

---

## PHASE D — Discoverability and honest failure · ✅ COMPLETE 2026-08-16 (Lane D 9836da6; D2 RLS live in prod)
**Depends on:** Phase A. Small, independent, safe.

- D1 — S2-1: `/attorney-referral` has no HomeHub tile or nav entry. Its only inbound link
  is buried in `CaseLawLookupFL.tsx`'s disclaimer section
- D2 — Legacy 422: returning users opening Deadlines on a pre-fix document get a bare 422.
  Needs an empty-state explaining the document predates text storage and asking for a
  re-upload. The 45 originals are unrecoverable — no storage bucket ever held them
- D3 — `token_estimate` key mismatch, `routes.py:288`. Sessions created with
  `token_count=0`. Bookkeeping only

---

## PHASE E — The referral path (G4) · ✅ COMPLETE 2026-08-16 (referral tables + RLS live via CI; G4 closed)
**Sequential. Each step gates the next.**

1. **S1-5 decision — Joe's.** Recommendation: unset `DEEPSEEK_API_KEY`, observe what
   degrades, then repoint surviving call sites to Haiku. Consolidates to one disclosed
   provider and closes the undisclosed-processor gap. The referral intake fallback loses
   nothing (Haiku is primary); `opinion_retrieval.py` query synthesis is the likely casualty
2. Write RLS for `attorney_inquiries` and `user_profiles`. **Do not apply the 20260813
   migration before this exists**
3. Apply the migration (manual paste until G3)
4. S1-3b — gate `/intake` and `/submit`, coordinated with the frontend caller
   (`AttorneyReferralFL.tsx` uses raw `fetch()` with no key; switch it to the `api.js`
   axios client)
5. S1-3 — `upsert_user` overwrites an existing profile matched on a client-supplied email
   with no ownership verification. Needs a verification step before it can upsert by email

---

## PHASE F — Close the migration hole (G3) · ✅ COMPLETE 2026-08-17
**The oldest open question. Nothing applies migrations; prod was hand-edited at least four times.**

- F1 — Build a CI migration step: apply `supabase/migrations/` on merge to main, in order,
  idempotently, failing the deploy on error
- F2 — Run `parity_check.py` in CI. Fail the build on drift
- F3 — Re-apply the closure seed, the `filings` migration, the `app_config` migration, and
  the cron amendment **through** the new mechanism, to prove it and make prod reproducible
- F4 — Backfill migrations for the four hand-drifted tables (`legal_opinions`,
  `court_forms`, `usage_stats`, `users`) so the schema is declared, not folklore

**CORRECTION 2026-08-17 — F2 claim-vs-reality gap (recorded, not silently fixed).**
Phase F was marked COMPLETE while F2 was unwired: parity.yml existed but its push
trigger was commented out, it had zero CI runs, and the repo held no
SUPABASE_URL / SUPABASE_SERVICE_KEY secrets — a dispatch would have failed. The
parity evidence behind G3's closure was manual shell runs only. F2 is now wired
for real: push trigger + nightly 06:00 UTC schedule + a green CI run. This
mismatch — a checklist marked done while the mechanism did not exist — is
exactly the failure class this plan targets; it is flagged here rather than
quietly amended.

---

## PHASE G — Cleanup. Only on Joe's explicit word. · ✅ COMPLETE 2026-08-17 (f145dd8) — analysis router (S2-6), push_tokens endpoint + save_push_token + empty mobile/ submodule, 5 dead frontend components + POST /eligibility, deprecated get/set_user_supplied_service_date helpers removed; trigger_events user_* columns dropped via CI. push_tokens TABLE drop released 2026-08-18 (Joe's ruling; table verified empty) and applied via CI (20260817000000_g_drop_push_tokens.sql).
- S2-6 `/api/analyze/*` — dead or broken. Deletion deferred here since Phase 2
- `push_tokens` / `mobile/` empty directory, pending C4
- Dead-code deletions the original INTEGRATION_PLAN ordered and nobody performed
- The three merged branches Joe skipped deleting

---

## PHASE H — Rebuild the documents · ✅ COMPLETE 2026-08-17 (afda816) — SPEC_LEDGER + INTEGRATION_PLAN rebuilt against f145dd8, docs/ADRS.md (3 ADRs), docs/VERIFY.md + scripts/verify_docs.py + `make verify-docs` (114/114)
**Last, deliberately.** Rebuilding the ledger before the code settles means doing it twice.

- `SPEC_LEDGER.md` and `INTEGRATION_PLAN.md` to production grade: per entry — capability,
  owner, status from a defined vocabulary, code path, test path, last-verified date and SHA
- Explicit "not built / deferred / rejected" sections so absence is legible
- The case-law ADR from `DECISIONS.md`, verbatim, correcting the stale LLM claim
- An ADR recording that uploaded documents are never persisted — state whether that is
  deliberate data minimization or an accident, because it determines whether reprocessing
  is ever possible
- `VERIFY.md` or a make target that mechanically proves the ledger's claims

---

## PHASE I — P&C Claim Guide module
**Recorded 2026-08-15. NOT scoped, NOT dispatched.**
Spec committed 2026-08-17 at docs/pc-claim-guide-module.md (+ research playbook
docs/property-casualty-claim-playbook.md — the FL statutory research it builds
on). The module is not yet built.

---

## PHASE J — Defect-category retrieval (SUPERSEDED 2026-08-27, close pending pop-os)

Branch `feat/defect-category-retrieval` (renamed from `docs/integration-plan-p2-status`
2026-08-18 — the old name misdescribed it). Content: `defect_category` propagation
into case-law retrieval with tag-relevance re-ranking (~170 lines; police_report_v2.py,
opinion_retrieval.py, test_opinion_mapper.py). Joe's ruling: KEEP, do not merge.
Predates the audit; needs a fresh review against current main before any merge.
NOT scoped, NOT dispatched. Recorded here so it stops being an unspoken branch.

**Joe's ruling 2026-08-27 — SUPERSEDED:** the cron implementation (2d9d86c3ca33,
skill legalclear-police-report-caselaw-fix) is more complete and includes the
Supabase-statement-timeout redesign; it supersedes the branch. Merged to main at
79fa02f after a green Phase 3 live gate (5/5 criteria). The branch exists ONLY on
pop-os (never pushed to origin). REMAINING TO CLOSE PHASE J: when pop-os returns,
diff the branch against the merged implementation for anything it has that the
merged version lacks, then delete the branch. Phase J closes with that.

The logged rule (FOLLOW_UPS): case-law results never present a charge class more
severe than the report's own charges; operationally, homicide cases are excluded
whenever the report has no homicide charge, and thinning results stay thin.

## Sequencing

```
A ✅ ──┬── B (critical path, gates G1) ──┐
       ├── C ──────────────────────────── ┤
       ├── D ──────────────────────────── ┼── H
       ├── E (gates G4) ───────────────── ┤
       └── F (gates G3) ───────────────── ┘
                                       G (on request)
```

B is the critical path. C, D, E, F are parallelizable but **run serially anyway** —
concurrent branches on overlapping files is how you get four PRs that each pass and
collectively break something.

---

## Open items Joe owes decisions on

| # | Decision | Blocks |
|---|---|---|
| 1 | S1-5 — DeepSeek: drop / gate+disclose / status quo | Phase E entirely |
| 2 | B1 — if service date is unextractable, ask the user or refuse to compute? | G1 |
| 3 | B4 — canonical disclaimer source (recommendation: `apply_disclaimer`) | B4, and the deferred pc-upl branch |
| 4 | C2 — email delivery provider | Reminder feature; first reminder fires 08-18 |
| 5 | C4 — mobile app: build or remove `push_tokens` | Phase G scope |
| 6 | Uploaded-document persistence — deliberate minimization or gap? | Phase H ADR |
