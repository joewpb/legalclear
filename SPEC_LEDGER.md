# SPEC_LEDGER.md — LegalClear capability ledger

**Rebuilt 2026-08-17 against main @ `f145dd8`** (Phase H). This rebuild corrects
**audit finding 7**: the previous SPEC_LEDGER (last verified 2026-06-30/07-05) was
materially false in places — it listed the analysis router as live (deleted in
Phase G, S2-6), described case-law lookup as an LLM call (it is deterministic ILIKE
retrieval — see `docs/ADRS.md` ADR-1), and carried a model registry that omitted the
DeepSeek call sites (since retired, Decision 7).

Every code path and test path below is mechanically checked by
`scripts/verify_docs.py` (`make verify-docs`). See `docs/VERIFY.md`.

---

## Status vocabulary

| Status | Meaning |
|---|---|
| **LIVE** | Deployed and reachable by users end-to-end (backend route + frontend surface where applicable). |
| **DARK** | Code is present and merged but intentionally not active (feature-flagged off, or missing a required credential). |
| **HEADLESS** | Backend capability with no frontend surface, by design (internal or machine-consumed). |
| **DEFERRED** | Explicitly decided to postpone; recorded with the decision that deferred it. |
| **REJECTED** | Considered and explicitly decided against; recorded with the decision. |
| **NOT_BUILT** | Planned/recorded but no code exists in the tree. |
| **AMBIGUOUS** | Exists in the tree but has no consumers and no decision on retire-vs-wire; awaiting Joe. |
| **UNVERIFIED** | Could not be verified from the tree on the last-verified date; claim is inherited, not proven. |

---

## Capability ledger

All rows: last verified **2026-08-17** at SHA **f145dd8**. Paths are repo-relative.

| Capability | Owner (agent/module/file) | Status | Code path | Test path | Verified | SHA |
|---|---|---|---|---|---|---|
| Document upload + ingestion (core) | `backend/src/api/routes.py` `/upload` + `backend/src/ingestion/pdf_parser.py` | LIVE | `backend/src/api/routes.py`, `frontend/src/pages/UploadFlow.jsx` | `backend/tests/test_upload_text_key.py`, `backend/tests/test_upload_token_estimate.py` | 2026-08-17 | f145dd8 |
| Document processing / explain pipeline | `backend/src/agents/explainer.py`, `backend/src/agents/risk_scanner.py`, `backend/src/agents/form_guide.py` | LIVE | `backend/src/api/routes.py`, `frontend/src/pages/ResultsPage.jsx` | `backend/tests/test_process_endpoint.py` | 2026-08-17 | f145dd8 |
| Document-type classifier (pipeline) | `backend/src/agents/classifier.py`, `backend/triage/classify.py` | LIVE | `backend/triage/classify.py`, `backend/triage/router.py` | `backend/evals/ground_truth.json` (eval harness `backend/evals/run_all.py`) | 2026-08-17 | f145dd8 |
| Deadline engine (extract → deterministic compute) | `backend/deadline/pipeline.py` | LIVE | `backend/deadline/extract.py`, `backend/deadline/compute.py`, `backend/deadline/rules.py`, `backend/deadline/pipeline.py` | `backend/tests/test_deadline_compute.py`, `backend/tests/test_deadline_pipeline.py`, `backend/tests/test_anchor_gate.py` | 2026-08-17 | f145dd8 |
| Deadline API (list/analyze/recompute) | `backend/src/api/routers/deadline.py` | LIVE | `backend/src/api/routers/deadline.py` | `backend/tests/test_deadline_router_idor.py`, `backend/tests/test_deadline_disclaimer.py`, `backend/tests/test_deadline_recompute_escalation.py` | 2026-08-17 | f145dd8 |
| User-supplied service facts (B5-f3/f4) | `backend/deadline/pipeline.py` + `document_service_facts` table | LIVE | `supabase/migrations/20260815000002_b5f3_document_service_facts.sql`, `backend/deadline/pipeline.py` | `backend/tests/test_deadline_service_date.py` | 2026-08-17 | f145dd8 |
| AI Intake (HomeHub situation router) | `backend/src/api/routers/intake.py` (inline Haiku call) | LIVE | `backend/src/api/routers/intake.py`, `frontend/src/pages/HomeHub.tsx` | `backend/tests/test_intake_router.py` | 2026-08-17 | f145dd8 |
| Small Claims Explainer | `backend/src/agents/small_claims.py` | LIVE | `backend/src/api/routers/small_claims.py`, `frontend/src/pages/SmallClaimsExplainer.tsx` | `backend/tests/test_small_claims_disclaimer_sse.py` | 2026-08-17 | f145dd8 |
| Small Claims Filing Wizard | `backend/src/services/packet_builder.py` | LIVE | `frontend/src/pages/SmallClaimsFL.tsx` | `backend/tests/test_phase_16.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Criminal Procedure Explainer | `backend/src/agents/criminal_procedure.py` | LIVE | `backend/src/api/routers/criminal.py`, `frontend/src/pages/CriminalProcedureExplainer.tsx` | `backend/tests/test_criminal_disclaimer_sse.py` | 2026-08-17 | f145dd8 |
| Discovery Motion Analyzer | `backend/src/agents/discovery_motion.py` | LIVE | `backend/src/api/routers/discovery.py`, `frontend/src/pages/DiscoveryMotionAnalyzer.tsx` | `backend/tests/test_discovery_motion.py`, `backend/tests/test_discovery_disclaimer_sse.py` | 2026-08-17 | f145dd8 |
| Property & Casualty Explainer | `backend/src/agents/property_casualty.py` | LIVE | `backend/src/api/routers/property_casualty.py`, `frontend/src/pages/PropertyCasualtyExplainer.tsx` | `backend/tests/test_pc_deadlines.py`, `backend/tests/test_pc_upl.py` | 2026-08-17 | f145dd8 |
| Wills & Trusts Explainer | `backend/src/agents/wills_trusts.py` | LIVE | `backend/src/api/routers/wills_trusts.py`, `frontend/src/pages/WillsTrustsExplainer.tsx` | `backend/tests/test_wills_trusts_disclaimer_sse.py` | 2026-08-17 | f145dd8 |
| Police Report Analyzer (+ opinion retrieval) | `backend/src/agents/police_report_v2.py`, `backend/src/services/opinion_retrieval.py` | LIVE | `backend/src/api/routers/police_report.py`, `frontend/src/pages/PoliceReportAnalyzer.tsx` | `backend/tests/test_opinion_mapper.py`, `frontend/src/components/policereport/sseMerge.test.ts` | 2026-08-17 | f145dd8 |
| Case Law Lookup (deterministic — ADR-1) | `backend/src/api/routers/case_law.py` (ILIKE over `legal_opinions`, **no LLM**) | LIVE | `backend/src/api/routers/case_law.py`, `frontend/src/pages/CaseLawLookupFL.tsx` | `backend/tests/test_phase_22.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Expungement (FL) | `backend/src/agents/expungement.py` | LIVE | `backend/src/api/routers/expungement.py`, `frontend/src/pages/ExpungementFL.tsx` | `backend/tests/test_phase_17.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Landlord / Tenant defense | `backend/src/services/packet_builder.py` (shared) | LIVE | `backend/src/api/routers/landlord.py`, `frontend/src/pages/LandlordTenantFL.tsx` | `backend/tests/test_phase_18.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Traffic Citation Wizard | `backend/src/services/packet_builder.py` (shared) | LIVE | `backend/src/api/routers/traffic.py`, `frontend/src/pages/TrafficFL.tsx` | `backend/tests/test_phase_20.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Forms Finder (443 published forms + AI suggest) | `backend/src/api/routers/forms.py`, `backend/src/services/form_recommender.py` | LIVE | `backend/src/api/routers/forms.py`, `frontend/src/pages/FormsFinderFL.tsx` | `backend/tests/test_form_recommender.py`, `backend/tests/test_forms_disclaimer_sse.py` | 2026-08-17 | f145dd8 |
| Filing Packet builder | `backend/src/services/packet_builder.py`, `backend/src/services/pdfa_generator.py` | LIVE | `backend/src/api/routers/packet.py`, `frontend/src/pages/FilingPacket.tsx` | `backend/tests/test_phase_23.py` (integration, CI-excluded) | 2026-08-17 | f145dd8 |
| Payments / Stripe paywall | `backend/src/payments/` + `backend/src/api/routes.py` (`/subscribe`, `/webhook`) | DARK (Decision 1: `PAYMENTS_ENABLED` off; code kept, not deleted) | `frontend/src/pages/PaywallPage.jsx` | `backend/tests/test_payments_disabled.py` | 2026-08-17 | f145dd8 |
| Chat Expert (per-module drawer) | `backend/src/agents/chat_expert.py` | LIVE | `backend/src/api/routers/chat.py`, `frontend/src/components/ChatDrawer.tsx` | — (no dedicated test file in tree) | 2026-08-17 | f145dd8 |
| Attorney Referral intake | `backend/src/api/routers/attorney_referral.py` | LIVE | `backend/src/api/routers/attorney_referral.py`, `frontend/src/pages/AttorneyReferralFL.tsx` | `backend/tests/test_attorney_referral_auth.py`, `backend/tests/test_attorney_referral_disclaimer.py` | 2026-08-17 | f145dd8 |
| Find Legal Help (county legal-aid directory) | `backend/src/services/county_router.py` | LIVE | `frontend/src/pages/FindLegalHelpFL.tsx` | — (no dedicated test file in tree) | 2026-08-17 | f145dd8 |
| Law corpus (statutes / rules / closures) | `backend/src/api/routers/law.py` | HEADLESS (intentional — consumed by deadline engine and internal callers, no UI planned) | `backend/src/api/routers/law.py` | — (no dedicated test file in tree) | 2026-08-17 | f145dd8 |
| Reminders (scheduled processing) | `backend/src/core/reminders.py`, `backend/src/core/notifications.py` | HEADLESS (intentional — pg_cron driven) | `backend/src/api/routers/reminders.py` | `backend/tests/test_reminders.py`, `backend/tests/test_notifications.py` | 2026-08-17 | f145dd8 |
| Email delivery adapter (C2) | `backend/src/services/email_delivery.py` | DARK (Decision 8: provider-agnostic adapter shipped; no provider API key set — reminders fail honestly) | `backend/src/services/email_delivery.py` | `backend/tests/test_email_delivery.py` | 2026-08-17 | f145dd8 |
| UPL wall / disclaimers / URL filter | `backend/src/core/upl.py`, `backend/src/core/disclaimer.py`, `backend/src/core/escalation.py`, `backend/src/core/url_filter.py` | LIVE | `backend/src/core/upl.py`, `backend/src/core/url_filter.py` | `backend/tests/test_upl.py`, `backend/tests/test_url_filter.py` | 2026-08-17 | f145dd8 |
| PII redaction (ingestion) | `backend/src/ingestion/pii_redactor.py` | LIVE | `backend/src/ingestion/pii_redactor.py` | `backend/tests/test_pii_redactor.py` | 2026-08-17 | f145dd8 |
| Startup config validation / API-key fail-fast | `backend/src/core/config.py` | LIVE | `backend/src/core/config.py` | `backend/tests/test_startup_config_validation.py`, `backend/tests/test_config_apikey.py` | 2026-08-17 | f145dd8 |
| CI migration pipeline + schema parity (Phase F, gate G3) | `.github/workflows/migrate.yml`, `.github/workflows/parity.yml` | LIVE | `.github/workflows/migrate.yml`, `.github/workflows/parity.yml`, `scripts/parity_check.py` | `backend/tests/test_parity_check.py` | 2026-08-17 | f145dd8 |
| Triage router (API surface) | `backend/src/api/routers/triage.py` | **HEADLESS** — code retained (`triage.py` + `triage/router.py` + `test_triage_router.py`), route registration removed 2026-08-17 (Joe's ruling: RETIRE — zero callers, LLM cost exposure). The human-confirmation loop design is preserved for reuse. | `backend/src/api/routers/triage.py` | `backend/tests/test_triage_router.py` | 2026-08-17 | 8da62e7 |
| Compliance router (optional) | `backend/src/api/routes.py` (gated registration) | DARK (feature-gated behind `compliance/` package) | `backend/src/api/routes.py` | — (no dedicated test file in tree) | 2026-08-17 | f145dd8 |

Rows marked "integration, CI-excluded" reference server-dependent test files that
exist in the tree but are excluded from `.github/workflows/pytest.yml` (they need a
live backend on :8001). Backend unit-suite baseline at f145dd8: **352 passed,
1 skipped**.

---

## Not built

| Item | Detail |
|---|---|
| **P&C Claim Guide module (Phase I)** | NOT_BUILT. Recorded 2026-08-15 in `REMEDIATION_PLAN.md` (Phase I), not scoped, not dispatched. Sequenced after Phase F because it needs the migration mechanism for its content corpus and deadline rules. Spec committed 2026-08-17: `docs/pc-claim-guide-module.md` (module spec) + `docs/property-casualty-claim-playbook.md` (FL statutory research it builds on). |
| **ES opinion corpus** | NOT_BUILT (backlog). `legal_opinions` summaries are English-only; `OpinionCard.tsx` renders an ES honesty stamp instead. |

## Deferred

| Item | Detail |
|---|---|
| **Mobile app (C4)** | DEFERRED per Decision 9 (2026-08-15). Phase G removed the push-token endpoint, `save_push_token`, and the empty `mobile/` submodule. |
| **`push_tokens` table drop** | HELD. The drop migration is authored on branch `fix/g2-push-tokens-table-drop` and **NOT merged**; the table still exists in prod until Joe merges it. No code references `push_tokens` at f145dd8. |
| **Reminder email provider key** | The delivery adapter is merged but DARK until a provider API key (recommendation: Resend) is configured (Decision 8). |
| **Decision 6 attorney confirmation** | The § 48.183 posted-service later-of rule is live but pending confirmation by a Florida attorney before public announcement. |

## Rejected

| Item | Detail |
|---|---|
| **DeepSeek as an LLM provider** | REJECTED (Decision 7, 2026-08-15). All three call sites (`opinion_retrieval.py`, `orin_opinions.py`, attorney-referral fallback) repointed to Claude Haiku; enforced by `backend/tests/test_no_deepseek_in_production.py`. |
| **External-link allowlist** | REJECTED (Decision 4). Rule is *no external links*; enforced by a deterministic output filter (`backend/src/core/url_filter.py`) that strips every URL from agent output at the boundary. |
| **Refusing to compute when service date is unextractable** | REJECTED (Decision 2, 2026-08-15). The product asks the user (date + method, with "I don't know" → escalation), never silently refuses and never records the answer as an extracted fact. |
| **LLM-generated case-law retrieval over the full corpus** | REJECTED (ADR-1 in `docs/ADRS.md`). Deterministic ILIKE + pg_trgm chosen over tagging 425,850 rows with an LLM. |

## Removed at Phase G (must not reappear as live anywhere)

- Analysis router (`/api/analyze/*`) — **deleted** (S2-6). `backend/src/api/routers/analysis.py` no longer exists.
- Push-token endpoint + `DatabaseManager.save_push_token` + empty `mobile/` submodule — **deleted**.
- Top-level `POST /eligibility` — **deleted** (superseded by `/api/expungement/eligibility`, which remains).
- 5 dead frontend components (`AnalysisDashboard.jsx`, `LandingPage.jsx`, `ExpungementPage.jsx`, `PhaseStub.tsx`, `layout/Navbar.jsx`) — **deleted**.
- Deprecated `get/set_user_supplied_service_date` helpers — **deleted**; `trigger_events.user_*` columns dropped in prod via CI migration (`supabase/migrations/20260817010000_g_drop_trigger_events_user_columns.sql`).

---

## Known limitations (recorded, not blockers)

- **Rate-limit tiers (2026-08-17, RL-2):** LLM-calling routes = `10/minute` (wills_trusts, property_casualty, small_claims ×2, discovery, criminal, police_report ×2, chat, intake, forms/suggest, attorney_referral/intake). Deterministic routes = `60/minute` (case_law/search, packet/build — Postgres round-trips, no LLM; VERIFIED no model calls). Expungement router routes carry NO limit: `/eligibility` is deterministic disqualifier matching and `/generate` is Stripe+PDF — neither calls an LLM (VERIFIED 2026-08-17); the LLM `ExpungementAgent` runs only in the `/api/upload` pipeline in routes.py.
- **Rate-limit storage is per-process memory (slowapi MemoryStorage, no `storage_uri`).** Rate limits reset on every Railway deploy/restart and are per-instance — they do not survive restarts and would not be shared across workers if the app ever runs more than one. Recorded 2026-08-17 (RL-1, VERIFIED against the installed slowapi package). Also: the limiter keys on `X-Real-IP` (Railway's edge-set header, documented in Railway's Specs & Limits) with XFF-leftmost and remote-address fallbacks; spoofed X-Forwarded-For is ignored when X-Real-IP is present.

## Change protocol

- Locate the capability's row before writing code; no row → write the row (and a spec) first.
- A row whose status is AMBIGUOUS or UNVERIFIED blocks building on top of it.
- Update the row's Verified date + SHA **in the same commit** as the code change.
- Run `make verify-docs` before committing any edit to this file — it fails on any
  code/test path that does not exist in the tree.
