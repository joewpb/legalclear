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

---

# GROUP B (S3 silent failures) — run 2026-08-14

| # | Item | Status | Branch | Commit | Files touched | Test delta | Cost |
|---|---|---|---|---|---|---|---|
| 8 | S3-3 startup config validation | PASS | fix/s3-3-startup-validation | 423b470 | config.py, routes.py (startup hook), test_startup_config_validation.py (new) | +3 tests; CI-scope 199/1 | $0.82 |
| 9 | S3-4 closure-fetch must not silently compute | PASS | fix/s3-4-closure-fetch | 28ff4e2 | deadline/pipeline.py, test_deadline_pipeline.py (new) | +2 tests; CI-scope 198/1 | $1.00 |
| 10 | S3-5a intake outage → 503 | PASS | fix/s3-5a-intake-swallow | 74058e8 | routers/intake.py, test_intake_router.py (new) | +2 tests; CI-scope 198/1 | $0.63 |
| 11 | S3-5b discovery risk-parse log | PASS | fix/s3-5b-discovery-swallow | a6748b7 | agents/discovery_motion.py, test_discovery_motion.py (new) | +1 test; CI-scope 197/1 | $0.91 |
| 12 | S3-5c upl unparseable-date escalate | PASS | fix/s3-5c-upl-swallow | 0c86cd0 | core/upl.py, test_upl.py | +1 test (25 passed); CI-scope 197/1 | $0.50 |

Group B total: $3.86. Zero exhaustions (S3-5 split into three single-surface
dispatches per the skill instead of one 60-turn run). S3-1 remains blocked on the
migration-tooling answer.

## Design notes (Group B)

- S3-3: validation runs at FastAPI startup, NOT import — deliberately avoiding the
  S1-1 CI-collection pitfall. Required vars (SUPABASE_URL, SUPABASE_SERVICE_KEY,
  ANTHROPIC_API_KEY) fatal outside ENVIRONMENT=development, matching the triage entry.
  Divergence to review: S1-1 gates API_KEY unconditionally at import; S3-3 carves out
  development for the other creds. Decide at review time which policy wins.
- S3-4: chose the assumption_disclosure route over refusing computation — existing
  response fields carried it, no API shape change. Flag + forced escalation per
  deadline.
- S3-5b: run chose log-at-error over a new SSE event after reading the client
  (whitelists only risk_analysis; unmatched chunks corrupt the final parse). Scope
  discipline — correct refusal, surfaced here for review.
- S3-5c: check_escalation has no in-repo callers yet (pre-existing state, not a
  regression of this fix).
