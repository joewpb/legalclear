# Phase H — rebuild SPEC_LEDGER.md + INTEGRATION_PLAN.md + create VERIFY.md

Repo: joewpb/legalclear. Worktree: ~/code/lc-h (branch fix/h-rebuild-docs, cut from origin/main f145dd8). Model context: you are the Phase H documentation rebuild. The old SPEC_LEDGER.md and INTEGRATION_PLAN.md are MATERIALLY FALSE in places (audit finding 7). Rebuild against the tree as it exists TONIGHT (2026-08-17), not against what the old files claim.

## Current reality (verified 2026-08-17; re-verify anything you rely on)

- main @ f145dd8. Phases A–F complete, gates G1–G5 closed. Phase G merged today:
  analysis router deleted (S2-6), push_tokens endpoint + save_push_token + empty
  mobile/ submodule removed, 5 dead frontend components + POST /eligibility route
  removed, deprecated get/set_user_supplied_service_date helpers removed,
  trigger_events user_* columns dropped in prod via CI migration.
- The triage router (backend/src/api/routers/triage.py) is AMBIGUOUS (0 frontend
  consumers; Joe decision pending) — document it as such, do not touch it.
- push_tokens table drop migration is HELD on branch fix/g2-push-tokens-table-drop
  (authored, NOT merged).
- Backend suite baseline: 352 passed, 1 skipped (CI-scope ignores per
  .github/workflows/pytest.yml).

## Deliverables

1. **SPEC_LEDGER.md — production grade.** Top: a defined status vocabulary —
   LIVE / DARK / HEADLESS / DEFERRED / REJECTED / NOT_BUILT / AMBIGUOUS — with a
   one-line definition each. Then ONE ENTRY PER CAPABILITY with exactly these
   fields: capability | owner (agent/module/file) | status | code path | test
   path | last-verified date (2026-08-17) | last-verified SHA (f145dd8).
   Derive the capability list from AGENTS.md, phases/BUILD_PLAN.md, the audit
   feature table in INTEGRATION_PLAN.md, the ACTUAL routers in
   backend/src/api/routers/*.py, and the ACTUAL frontend routes in App.tsx.
   For anything you cannot verify from the tree tonight: mark the row
   UNVERIFIED in the status column. NEVER invent endpoints, counts, or paths.
2. **INTEGRATION_PLAN.md — rebuilt.** Keep its structure (confirmed state,
   audit table, integration orders, UPL guardrails, out-of-scope) but every row
   fact-checked against the current tree. Deleted things must not appear as
   live. Update: analysis router gone, push-token gone, /eligibility gone, dead
   components gone, triage still AMBIGUOUS, /api/law HEADLESS (intentional),
   Phase I recorded-only. Note at the top that this is the rebuilt version
   correcting audit finding 7.
3. **Explicit absence sections in SPEC_LEDGER:** "Not built", "Deferred",
   "Rejected" — include at minimum: P&C Claim Guide module = NOT BUILT
   (Phase I, spec at docs/pc-claim-guide-module.md, recorded only), mobile app =
   DEFERRED (Decision 9), triage router = AMBIGUOUS, push_tokens table drop =
   HELD (branch fix/g2-push-tokens-table-drop).
4. **ADRs — add a file docs/ADRS.md with these three, in this order:**
   a. The CASE-LAW ADR from DECISIONS.md, quoted VERBATIM (find it, copy the
      full ADR text), followed by the correction: state which LLM-produced
      claim it supersedes and where the stale claim lived.
   b. ADR: uploaded documents are never persisted. Read the upload flow
      (backend/src/api/routes.py upload endpoint + storage handling) and the
      recovery evidence, then state PLAINLY whether the non-persistence of
      originals is DELIBERATE DATA MINIMIZATION or an ACCIDENT. Record the
      consequence: documents with empty extracted text are unreprocessable.
      Decision status: ACCEPTED — name the actual basis in the evidence.
   c. ADR: user-supplied facts never live on pipeline-owned rows. Capture the
      B5-f1..f4 lesson: four variants of one design error (user date ignored;
      anchor gate fired before user-supplied consultation — dead code; freshly
      extracted method won at compute time; clobbering — user columns lived on
      pipeline-rewritten rows). Root rule: a user fact must never share a row
      with anything an automated pipeline rewrites; structural fix =
      document_service_facts + unconditional dedup on (document_id,
      governing_rule). Reference the files.
5. **VERIFY.md + scripts/verify_docs.py + Makefile target `make verify-docs`.**
   verify_docs.py MECHANICALLY proves the ledger's claims: for every code path
   and test path in SPEC_LEDGER, assert the file exists in the tree; exit
   non-zero on the first missing path, print PASS/FAIL per entry, end with a
   summary line. File-existence + grep-level assertions only (no network, no
   pytest). If no Makefile exists, create one with the verify-docs target.
   Run `make verify-docs` at the end and paste its full output (expect all
   PASS, exit 0).

## Hard rules

- No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
  (no curl/WebFetch). No railway/supabase commands. Edit in place — the
  orchestrator commits.
- Do not modify any code outside: SPEC_LEDGER.md, INTEGRATION_PLAN.md,
  docs/ADRS.md, docs/VERIFY.md (or VERIFY.md at repo root — pick one and be
  consistent), scripts/verify_docs.py, Makefile.
- Run the backend suite with the CI-scope ignores at the end to prove you
  broke nothing (baseline 352 passed, 1 skipped).
- Final answer: files changed, verify_docs.py output summary, suite result,
  the three ADR one-line summaries, and turn count.
