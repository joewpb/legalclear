# PHASE2_RUN_REPORT.md — LegalClear Phase 2 audit remediation, run 2026-08-13

Orchestrator: Hermes (VPS) dispatching headless Claude Code on pop-os (`joe@100.95.23.85`),
repo `/home/joe/code/legalclear`. Audit baseline `0c2e006` — origin/main unmoved
throughout the entire queue.

## Per-item ledger

| # | Item | Status | Branch | Commit(s) | Files touched | Test delta | Cost |
|---|---|---|---|---|---|---|---|
| 0 | Recon: Railway values + migration mechanism | PASS (report) | none | — | runs/00_recon/report.md | n/a | $0.48 |
| 1 | S1-1 API_KEY default removal + fail-fast | PASS | fix/s1-1-apikey-failfast | cc61ec8, 97c8f56 | config.py, test_config_apikey.py (new), FOLLOW_UPS.md, pytest.yml | +3 tests; CI-scope 199/1 (baseline 196/1) | $0.99 |
| 2 | Unauthenticated endpoint enumeration | PASS (report) | none | — | runs/02_auth_sweep/REPORT.md | n/a | $1.43 |
| 3 | S1-4 IDOR deadline GETs | PASS (2 runs) | fix/s1-4-deadline-idor | 077016e | deadline.py, ResultsPage.jsx, test_deadline_router_idor.py (new) | +3 tests; CI-scope 199/1 | $1.64 |
| 4 | S1-3 attorney-referral endpoint auth | PASS (2 runs + HALT) | fix/s1-3-referral-auth | fabaa4f | attorney_referral.py, test_attorney_referral_auth.py (new) | +4 tests; CI-scope 200/1 | $1.42 |
| 5 | Decision 1: PAYMENTS_ENABLED off + flag test | PASS | fix/paywall-off | bda53d2 | test_payments_disabled.py (new, 138 lines) | +7 tests; CI-scope 203/1 | $0.88 |
| 6 | S1-6 UPL wall — diagnose only | PASS (report) | none | — | runs/06_upl/REPORT.md | n/a | $2.10 |
| 7 | S1-5 PII→DeepSeek data-flow map | PASS (report) | none | — | runs/07_deepseek/REPORT.md | n/a | $2.41 |

**Total spend: $11.35** (incl. $0.14 smoke test). No run exceeded its budget; two runs
hit the 40-turn cap (items 3, 4) and were recovered per Joe's decisions, not by raising
budgets.

## main history (local, not pushed)

- `26e282c` docs: add S1-3b triage + S1-3 follow-ups to FOLLOW_UPS.md (Joe-ordered
  separate commit). Local main is 1 ahead of origin/main by design.

## Report documents (read-only items)

- runs/00_recon/report.md — migration mechanism: NO repo-based mechanism exists; manual
  ad-hoc application inferred. Railway values (API_KEY, PAYMENTS_ENABLED,
  DEEPSEEK_API_KEY): UNVERIFIED — require Joe's Railway dashboard.
- runs/02_auth_sweep/REPORT.md — 63 routes, 47 unauthenticated (2.4× DECISIONS "~20"
  estimate), 10 IDOR, 6 unthrottled LLM, zero "intentionally public" statements; dead
  endpoints and one broken frontend call (`/checkout/{documentId}`) identified.
- runs/06_upl/REPORT.md — UPL wall is a library not a wall; two parallel disclaimer
  sources; criminal/discovery streaming success paths unenforced; attorney_referral
  entirely outside the wall; client whitelist trap mapped; minimal fix footprint with
  file:lines; deploy coupling: client tolerance BEFORE backend event.
- runs/07_deepseek/REPORT.md — three DeepSeek call-sites ranked: referral intake
  fallback (verbatim PII, LATENT) > opinion_retrieval (synthesized findings from police
  report, LIVE iff key set) > orin_opinions (public text only, DEAD in prod). Zero
  disclosure in ToS. All three degrade gracefully without the key (zero-crash kill
  switch).

## Escalations raised to Joe during the run (all resolved)

1. Item 0: Railway secrets unreadable from repo — prohibition honored; values remain
   Joe's dashboard check. Blocks: S1-1 deploy gating, S1-5 liveness verdicts.
2. Item 1: fail-fast breaks CI collection (no API_KEY in Actions) — fixed with dummy
   `API_KEY: ci-test-key` env in pytest.yml (Joe-approved, no secret needed).
3. Item 3: turn exhaustion mid-fix — continuation run per Joe's template; completed.
4. Item 4: second consecutive turn exhaustion → queue HALT per rules — Joe's decisions:
   S1-3b logged in FOLLOW_UPS.md with dependency on S1-5; .tmp files deleted; verification
   run passed; commit split (branch + FOLLOW_UPS on main).
5. Revised caps applied for remainder: items 6/7 at 50 turns/$6 (both passed well
   under).
6. Dispatch hardening: disallowedTools extended beyond the base template with
   git reset/clean/stash/add/commit/branch to mechanically enforce the standing
   prohibitions; report-only runs restricted to their named report file.

## Not done / next per Joe

- S1-3b (gate /intake + /submit with coordinated frontend change) — blocked on S1-5
  decision.
- UPL fix run (S1-6/S3-2) — needs Joe's picks: disclaimer source standardization
  (get_disclaimer vs apply_disclaimer), event shape (typed recommended), ES language
  wrinkle, deploy ordering.
- S1-5 decision (drop / gate+disclose / status quo) — needs Railway DEEPSEEK_API_KEY
  lookup first.
- S1-1 deploy gating: confirm API_KEY set in Railway before merging/deploying the branch.
- All four fix branches await Joe's manual review. Nothing pushed, nothing merged.
