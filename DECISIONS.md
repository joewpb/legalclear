# DECISIONS.md — Approved decisions and work order for Phase 2 fix sessions

**Source:** Joe's triage review of `AUDIT_FINDINGS.md` (audit stamped at commit
`0c2e006665cd2d3d87ebc49d7a4adb7800ca6b55`), recorded 2026-08-13.
**Status of this file:** authoritative reference for the scoped fix sessions that
follow. Each fix session should read this file and `AUDIT_FINDINGS.md` before
touching anything.

---

## Decision 1 — Paywall: DISABLE, DO NOT DELETE

- Set `PAYMENTS_ENABLED` to false/off and **confirm the effective value in Railway**
  (`zesty-delight`).
- Keep ALL gating code in place. Do not remove payment code paths, tables, or
  dependencies — billing will be re-enabled later.
- Add a test asserting the flag is off and that no route is payment-gated while it
  is off.
- Report exactly what becomes reachable that was previously gated.

## Decision 2 — Case law: DOCUMENTATION ONLY. Do not touch case_law code.

Record the following as a decision record (ADR) in the Phase 3 document rebuild,
and correct SPEC_LEDGER's stale claim that case_law uses an LLM.

### ADR: Case law lookup is deterministic by design (verbatim)

> Case law lookup is deterministic database retrieval, not LLM. legal_opinions holds
> 425,850 Florida opinions. Only 759 rows (0.18%) ever received LLM-generated
> situation_tags, so tag-based retrieval returned empty for most searches. The options
> were to run an LLM over all 425,850 rows (thousands of dollars, weeks of API time) or
> search the already-populated plain-English summary column directly with Postgres ILIKE
> backed by a pg_trgm index — 100% row coverage, instant, zero cost. The deterministic
> path was chosen deliberately.
>
> Citation treatment (4,749 FL cases with negative treatment) is also deterministic:
> parsed from CourtListener's parentheticals bulk CSV with keyword rules, deliberately
> zero AI, because fabricated case citations carry felony-level risk.
>
> This follows the core principle in AGENTS.md: LLMs extract and explain; deterministic
> code computes and retrieves.
>
> LLM is used only in: document intake (classifier/risk_scanner/scanner/explainer),
> Police Report Analyzer, Discovery Motion Analyzer, Criminal Procedure Explainer,
> Property & Casualty Explainer, Small Claims Explainer, Wills & Trusts Explainer,
> Expungement analyzer, Form guidance, Forms /suggest, Attorney Referral intake chat,
> ChatExpert, and opinion-retrieval query synthesis.

Additionally record in the ADR: `opinion_retrieval.py` and `orin_opinions.py` use
DeepSeek, and the SPEC_LEDGER model registry is missing that provider entirely —
that gap is an **S1-adjacent disclosure problem, not a cosmetic one**.

---

## Work order — do not deviate

Phase 2 executes S1 first. **Stop after each group for Joe's review.**
One fix session per triage item (fresh session, small context), reading this file
and AUDIT_FINDINGS.md first.

### Group A — S1, all six. Priority order within the group:

1. **S1-1** `API_KEY` default `"testkey123"` (`backend/src/core/config.py:30`) —
   remove the default entirely; the app must **refuse to start** if `API_KEY` is
   unset. Never degrade to a default secret.
2. **S1-x (auth sweep)** The ~20 unauthenticated endpoints — **enumerate them with
   file:line before fixing**, and report which are intentionally public.
3. **S1-4** IDOR on deadline GETs (`routers/deadline.py:43,62`) — scope to the
   owning user.
4. **S1-2** Attorney-referral tables without RLS (`20260813000000_add_users_and_referrals.sql`)
   — do **NOT** apply that migration to prod until RLS is written. Flagged BLOCKED
   until the RLS amendment exists.
5. **S1-5** PII to DeepSeek in the three production paths — **do not change behavior
   yet.** Produce a written data-flow map: which fields, which endpoint, which
   provider, what is retained. Joe decides on disclosure/consent after seeing it.
6. **S1-6 / S3-2 (UPL)** UPL wall gaps — Criminal and Discovery streaming success
   paths, and the attorney-referral router.

### Group B — S3 silent failures (before S2 — they hide the real errors)

S3-1 (prod schema parity check), S3-3 (startup config validation), S3-4 (closure
fetch failure must not silently compute), S3-5 (intake/discovery/upl swallow fixes).

### Group C — S2, starting with the core product

The deadline→reminder pipeline has 45 documents and 45 sessions but 0
trigger_events, 0 deadlines, 0 reminders, 0 push_tokens. **Diagnose why it has
never executed end to end before changing anything.** Then the remaining S2 items
per AUDIT_FINDINGS §6.

### Group D — S4.

### Group E — S6 cleanup: ONLY if Joe explicitly asks. No deletions on the
assistant's own initiative.

---

## Standing rules for every fix session

- One PR per triage item or tightly coupled group. Squash-and-merge. **Never commit
  to main.**
- Every fix ships with a test that fails before it and passes after.
- No opportunistic refactoring. Fix the named defect only.
- `uv` only for Python. No pip, no poetry.
- No deletions during Phase 2.
- Config that is missing must raise loudly at startup, never degrade to empty.
- If origin/main moves during a session, stop and report the new SHA.

---

## Blocked items — waiting on Joe's Railway / migration-tooling answers

Joe is checking Railway env values and the migration-apply mechanism. Until
confirmed:

**Blocked on Railway answers:**
- S1-1 *verification half* (is `API_KEY` set in Railway? the code fix — remove
  default + fail-fast — is NOT blocked; deploying it safely requires knowing the
  Railway value first, since deploying fail-fast with `API_KEY` unset takes prod
  down).
- Decision 1 confirmation step (effective `PAYMENTS_ENABLED` in Railway).
- S1-5 data-flow map completeness (is `DEEPSEEK_API_KEY` set in prod? determines
  whether the DeepSeek paths are live or latent).

**Blocked on migration-tooling answer (what applies `supabase/migrations/` to prod):**
- S1-2 (RLS migration must land through a verified mechanism).
- S3-1 (schema parity check design depends on the intended mechanism).
- S2-1, S2-3, S2-4 (all require applying migrations/data to prod).

**Not blocked — can start immediately:**
- S1-1 code change (remove default, fail-fast at startup) — merge-ready, deploy
  gated on Railway confirmation.
- S1 auth sweep enumeration (read-only inventory + intentionally-public list).
- S1-4 IDOR fix on deadline GETs.
- S1-5 data-flow map (code-level map now; prod-liveness column filled in after
  Railway answer).
- S1-6 UPL wall fixes (criminal/discovery disclaimer events; attorney-referral
  `apply_disclaimer` wrap — code-only, no schema dependency).
- S1-3 attorney-referral endpoint auth (code-only; tables need not exist to add
  auth).
- Decision 1 test (flag-off assertion test is code-only).
## Decision 3 — Canonical disclaimer source: `apply_disclaimer` (2026-08-15)
Single versioned source, imported by every path. `get_disclaimer` and `deadline.py`'s
inline disclaimer text are SUPERSEDED. External links (floridalawhelp.org,
floridabar.org) removed per the no-external-links rule. This unblocks
fix/pc-upl-stale-tests (rewrite its assertions against apply_disclaimer).

## Decision 2 — Service date: ASK THE USER, do not refuse to compute (2026-08-15)
All mandatory constraints:
- Service date stored with provenance `user_supplied`, never extracted. Distinct field,
  distinct audit trail. It must never be recorded as an extracted fact.
- Deadline presented conditionally: "If you were served on X, your response is due Y."
- Input remains visible and editable; correction recomputes the deadline.
- "I don't know" escalates and does NOT compute. Tell the user the return of service is
  filed with the clerk and the case docket shows the service date.
- Ask HOW service occurred, not only when. Fla. Stat. § 48.183 permits service by
  posting when the tenant cannot be found; a tenant who found papers on the door may
  not know the actual service date. Method affects the analysis.
## Decision 4 — External links: deterministic output filter, NOT an allowlist (2026-08-15)
Strip every URL from generated agent output at the boundary. Log each stripped URL with
the agent name so emission rates are visible. Rationale: prompt edits cannot guarantee
the rule (proven by B4b-1a); models also invent plausible legal-aid domains that may be
dead or squatted, and directing a distressed user there is a real harm. An allowlist
implies endorsement and requires perpetual maintenance; the rule is no external links,
so enforce exactly that. Consistent with AGENTS.md: LLMs generate, deterministic code
guarantees.

## Decision 5 — Disclaimers on error paths: conditional on emitted content (2026-08-15)
An error carrying no substantive content needs no disclaimer — deadline.py's bare
{"detail"} is correct and needs no change. An error occurring AFTER substantive content
has been emitted MUST carry the disclaimer, because the user is left holding legal
analysis with no wall. Applies to the streaming routers only.
## Decision 6 — § 48.183 posted service: later-of computation (2026-08-15)
Fla. Stat. § 48.183(2): service by posting is effective on the date of posting OR the
date of clerk mailing, whichever occurs LATER. The clerk mails a copy and files a
certificate of the fact and date of mailing.
- The prior code was WRONG: posting fell into publication/unknown and computed the
  EARLIER of personal-or-mail variants. Required: posted becomes its own
  service_method bucket computing from the LATER of posting date and clerk-mailing
  date.
- Product consequence (mandatory in B5): a tenant knows the posting date but cannot
  know the clerk-mailing date. For posted service, the UI must capture the posting
  date AND direct the user to the case docket for the mailing certificate. If the
  mailing date is unavailable, ESCALATE — do not compute from the posting date alone.
- PENDING CONFIRMATION by a Florida attorney before shipping.

**UPDATE 2026-08-18 — legal answer received, matches this decision.**
Source: Joe relayed a legal answer on § 48.183(2) that confirms the
later-of computation. **ATTRIBUTION PENDING** — the answering attorney's
name has not been provided to the executor; G1 does not open on an
unattributed answer. Record the attorney's name and the date of the
opinion here when supplied.
The confirmation also covers the substitute-service timing: substitute
service under § 48.183(2) (delivery to a qualified co-resident) uses the
same day-after + 5-business-day treatment as personal service — the
compute engine collapses `substitute` into the personal path (no own
branch), which three worked-example tests now lock:
`backend/tests/test_decision6_worked_examples.py` (personal 08-10→08-17,
substitute 08-10→08-17, posted 08-10+mail 08-12→08-19; all passing).
## Decision 7 — DeepSeek retirement (closes S1-5) (2026-08-15)
Repoint all three DeepSeek call sites — opinion_retrieval.py, orin_opinions.py,
attorney-referral fallback — to Claude Haiku. After that deploys and verifies,
Joe unsets DEEPSEEK_API_KEY in Railway. One disclosed provider, gap closed.

## Decision 8 — Email delivery (C2) (2026-08-15)
Provider-agnostic delivery adapter; the concrete provider is configuration
(recommendation: Resend). If no API key is available tonight, the adapter ships
DARK and reminders keep terminating failed until the key lands. Acceptable.

## Decision 9 — C4 mobile (2026-08-15)
DEFERRED. push_tokens logged for Phase G. No work tonight.

## Decision 10 — Session tokens DEFERRED (2026-08-17)
Mitigation #3 (short-lived server-issued session tokens) is deferred: it should
ride the user-accounts work required by the G2 payments gate rather than being
built standalone. Mitigations 1 (Anthropic spend caps/alerts — Joe configuring)
and 2 (per-IP rate limiting, XFF fix first) proceed now. S1-8 remains open until
#3 lands; the spend cap bounds worst-case cost meanwhile.

## Decision 11 — No attorney review; educational framing is the codebase-wide output standard (2026-08-18)
LegalClear is an educational platform. There will be no attorney sign-off on
the deadline rules at this stage; attorney referral is a later, separate
offering. Decision 6's "attorney confirmation" requirement is REPLACED —
deliberately traded, not satisfied — by an output standard that applies to
EVERY user-facing output from here forward (recorded in AGENTS.md as core
principle 2b). Every computed or generated output must show:
  1. The governing statute or rule, with citation.
  2. The inputs used, and where each came from (user-supplied vs extracted).
  3. The reasoning trace — the counting, the matching, the steps — not just the result.
  4. An instruction to verify against the court docket or an official source.
  5. Framing as "here is how the rule computes" rather than "here is your answer".
The engine already produces the trace; the gap is presentation. The
§ 48.183(2) answer received 2026-08-18 stands as research input, not as an
attorney review. Surfaces audited 2026-08-18; fixes sequenced after Joe's
slice ruling.

**Addendum (2026-08-18) — advice-phrasing check removed from verify_educational.py:**
Check #4 (regex-based detection of "you must" / "you should" / "your deadline
is" / etc. in user-facing strings and agent prompts) was built, run against
the codebase, and removed on evidence. Two of its three hits were
CaseLawLookupFL's "you should double-check/verify" lines — exactly the
verify-against-an-official-source instruction item 4 above requires. Regex
phrase-policing can't distinguish required verification language from
prohibited advice-giving; it flagged the former as the latter and would have
pushed toward stripping the safety instruction to pass the checker. Second-person
guidance and substantive legal explanation are the product's purpose — the
educational-framing standard is about what backs a statement (citation,
inputs, trace, verify-instruction, "here is how" framing), not about avoiding
the word "you" or the verb "should". The checker now runs 4 checks (citation
fields, reasoning trace, no unsanctioned URLs/domains, single canonical
disclaimer source); advice-phrasing detection is not coming back as a static
regex check.

## Decision 12 — Statutes corpus was stubs; rebuilt with real validation (2026-08-18)

The owned `statutes` rows for ch. 34/83 were heading-only stubs (e.g. § 83.60 = 147 chars vs ~2,900 official; § 83.45 = 30 chars). Root cause: `ingest_statutes.py`'s span-terminated parser ended body capture at the first nested `</span>` inside SectionBody, keeping only the first subsection label + History footer.

Decided: (1) the citation work's premise — verification against OWNED TEXT — was false until the corpus held real text; J3 merge + J4 prose filter were blocked until rebuild + re-verification. (2) The parser was rewritten mode-based (SectionBody span is a start marker; capture persists across nested spans until the History div). (3) Re-ingestion used fetch → validate → replace per section: empty-body records are skipped with the old row untouched; short-but-genuine statutes are ingested with their official text and reported. (4) Validation was replaced: "text present" (which passed on headings) is gone; the new checks are min-length reporting (every section under 120 chars named), empty-body rejection, and a 10% sample length-ratio check against official per-section pages. Result 2026-08-18: ch. 34 17/17 and ch. 83 74/74 re-ingested; sample 9/9 ratios 0.99–1.08; the ch. 34 pilot's 17 all re-verify against real text (16 body-OK, 1 genuinely short § 34.171 verified against source). The original pilot report's "verified" claim is recorded as true-as-stated, misleading-in-effect; the new standard is body detection + ratio sampling, not presence.

## Decision 13 — Conditional framing is the house voice (2026-08-18)

Two doctrines, both recorded in AGENTS.md (2c, 2d):
1. **Generalized versus individualized.** Generalized legal explanation is unlimited — what the law says, how a rule computes, what defenses exist, what a filing does, what a party must prove. Applying law to the user's specific facts as a directive is what the attorney referral is for. The distinction is generalized versus individualized, not cautious versus rich.
2. **Conditional framing over directives.** "If you file a motion to determine rent within the answer period, the disputed rent goes into the court registry and your defense is heard on the merits. If you don't, § 83.60(2) allows the landlord to move for default and the court can enter judgment without reaching your defense." Both branches developed honestly; a lopsided conditional is a directive in disguise. Where not acting is genuinely reasonable, say so. A richness requirement, not a hedging requirement.

Applied to all seven prose agent prompts (explainer, small_claims, criminal, discovery, wills_trusts, property_casualty, chat) in the K1–K3 dispatches, with output-level verification per the B4b-1a lesson.

## Decision 14 — Parser agreement proves existence, not text fidelity (2026-08-20)

Two independent parsers, same official PDFs, 82 shared rule rows: 0 byte-identical, 9 identical after whitespace normalization, 73 differing — each parser mangling a different ~half at page boundaries. Agreement between independent parsers proves citation EXISTENCE (the property the CitationFilter needs — it is keys-only), not text fidelity. Text fidelity requires ratio-checking against the source, per document — the same distinction as presence versus completeness (Decision 12). Consequence applied: per-rule best-side merge of the 82 shared rules with the official PDF as arbiter (36 rows updated from the Orin parse, 46 kept; pre-merge backup written). Also routed Orin's 30 harvested FORM rows into court_forms (22 inserted, 8 skipped on existing form_number, status='review' + review_reason marking harvested-not-curated) — this does NOT close the form_guide audit finding (form_guide still reads its hardcoded library, not the table).

## Decision 15 — No PR flow: checks stay running-and-visible, not required (2026-08-22)

Ruling on the required-status-checks question (Job 2 cost report, 2026-08-21):
no PR flow. A solo developer with self-approval makes the gate ceremonial —
approving one's own PRs is theater. Checks running and visibly red on every
push capture most of the value at none of the cost (no per-dispatch approval
latency, no STATUS-regen churn, no admin-bypass carve-out that quietly
un-gates the gate).

GitHub required status checks gate PR merges only — they do not block direct
pushes, and `enforce_admins` is false, so with the current direct-to-main
dispatch flow they would change nothing unless the whole flow moved to PRs.

**Revisit when a second person commits to this repo.** Until then, the
discipline rule holds: the orchestrator gates every dispatch on green CI
before pushing to main.

## Decision 16 — English first; Spanish deferred until the English product is complete and live (2026-08-23)

Scope ruling (Joe, Phase I finale): Spanish is out of scope until English is
fully working. Consequences applied:
- test_spanish (test_phase_23.py) stays skipped — deferred-by-decision, NOT
  environment-broken.
- The ES i18n audit item moves to recorded-not-scheduled in FOLLOW_UPS.md
  with this ruling as the reason.
- No Spanish path is built, tested, or verified in the remaining Phase I
  slices. The language parameter remains wired end-to-end (AGENTS.md §7:
  no re-architecture required) — this is deferral, not removal.

## Decision 17 — Ledger surgery is prohibited; repairs are always a NEW forward migration (2026-08-24)

The 2026-08-23 "B5 repair" deleted schema_migrations ledger rows and re-ran
the B5 ADD COLUMN files after G4 (20260817010000) had dropped the
trigger_events user_* columns — regressing G4's end-state and re-creating
columns the schema set says must not exist. Ruling (Joe):

- Deleting or rewriting schema_migrations rows is PROHIBITED. The ledger is
  write-once; a row records that a file was applied, never a knob for what
  should have run.
- Migration-state repairs are ALWAYS a new forward migration file that moves
  the schema toward the declared end-state. 20260824000001 re-applies G4's
  drops doctrine-clean; 20260824000000 and 20260824000002 continue forward.
- Baseline seeds (20260518000000) cover the manual pre-CI era, so "ledger
  says applied" never proves "CI executed the DDL". Parity is the net that
  catches schema drift regardless of ledger state.
- Consequence of this incident: the remediation dispatch's "PR flow" line is
  overridden — Decision 15 stands (no PR flow; direct push after green CI).

## Decision 18 — Phase J supersession (2026-08-27)

- The cron implementation of the police-report caselaw fix (job 2d9d86c3ca33,
  skill legalclear-police-report-caselaw-fix) SUPERSEDES the pop-os branch
  `feat/defect-category-retrieval`: it is more complete and includes the
  Supabase-statement-timeout redesign. Merged to main at 79fa02f after a green
  Phase 3 live gate (5/5 criteria, incl. mapper-hash pin).
- Charge-context exclusion (hard, deterministic, testable): homicide cases are
  EXCLUDED from case-law results whenever the report carries no homicide
  charge; exclusion thins but never backfills. Non-homicide charge classes
  are NOT filtered (Joe's example: Caldwell stays for misdemeanor reports).
- Anchor queries advance on junk-only / below-threshold results, not just on
  exceptions; multi-anchor pools are unioned and deduped by cluster_id.
- Gate discipline: the Phase 3 gate asserts only what is deterministic —
  mapper source hash, live derive consistency, substantive-tag-set subset,
  homicide-exclusion on output. LLM output variance is NOT a code regression
  and must not fail a gate.
- Phase J closes when pop-os returns: diff the branch against main for
  anything it has that the merged implementation lacks, then DELETE the
  branch. The branch lives only on pop-os; it was never pushed to origin.
