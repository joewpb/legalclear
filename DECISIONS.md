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
