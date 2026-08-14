# AUDIT_FINDINGS.md — Full Audit & Reconciliation, Phase 1 (Diagnosis Only)

**Audited commit:** `0c2e006665cd2d3d87ebc49d7a4adb7800ca6b55` (origin/main, verified unmoved at audit end)
**Audit date:** 2026-08-13
**Method:** read-only code inspection + read-only queries against production Supabase (row counts / table existence only; no user data read beyond `court_closures` reference rows). Local test suite and fast-mode eval harness executed. No source files modified. This file is the only write.
**Framing honored:** `SPEC_LEDGER.md` and `INTEGRATION_PLAN.md` treated as unverified claims and checked against code and production state.

---

## 1. EXECUTIVE SUMMARY

### Status counts (36 traced capabilities, §3)

| Status | Count |
|---|---|
| WORKING | 17 |
| PARTIAL | 7 |
| CODED_NOT_WIRED | 4 |
| WIRED_NOT_REACHABLE | 2 |
| PHANTOM | 3 |
| MISSING | 1 |
| UNDOCUMENTED | 2 |

### The five most consequential problems

1. **Production schema does not match the repo's migrations — migration application is nondeterministic.** `user_profiles`, `attorney_inquiries` (20260813) and `filings` (20260704) **do not exist in prod** (PostgREST 404 with service key), while `citation_treatment` (20260812) does. The 20260808 circuit-closures seed (~90 rows) never applied: prod `court_closures` holds only the 9 statewide 2026 holidays from May. Whatever process is believed to auto-apply migrations on merge is not doing so reliably. Everything downstream of a missing table is broken silently.

2. **The core promised product — deadline extraction → computation → reminders — has never functioned in production.** Prod counts: `documents` 45, `sessions` 45, but `trigger_events` **0**, `deadlines` **0**, `deadline_reminders` **0**, `push_tokens` **0**. The pipeline is coded, tested (196 unit tests pass; eval gate 34/34 fatal), and wired in the UI (ResultsPage compute-on-demand → `POST /api/deadline/analyze/{id}`), but no deadline has ever been stored. Reminders additionally depend on an unconfigured pg_cron caller (open manual gap since Phase 6) and an email stub that by design never delivers. The flagship feature is a complete, verified machine that has never run end-to-end for a real user.

3. **Auth is a single shared static key whose server-side default is the publicly known `"testkey123"`** (`backend/src/core/config.py:30`). If Railway's `API_KEY` env var is unset, every `verify_api_key`/`require_api_key` endpoint (upload, process, document read, chat, user create, subscribe, reminders trigger, triage) accepts `testkey123`. Even when set, the key ships in the JS bundle (`VITE_API_KEY`) and is public by definition. Meanwhile ~20 endpoints — including all six streaming LLM explainers, chat, intake, forms/suggest, attorney-referral, case-law, packet, landlord/traffic/expungement generate — have **no auth at all**, and several LLM endpoints have **no rate limit** either (§4.9, §4.6). Tenancy: any holder of the key (or nothing, for deadline GETs) can read any user's documents, deadlines, and chat by ID (IDOR).

4. **User PII flows to DeepSeek (third-party, non-US LLM provider) in three production paths** — police-report analysis excerpts (`services/opinion_retrieval.py:246-262`), criminal-module analysis (same helper), attorney-referral intake conversations incl. name/phone/email (`routers/attorney_referral.py:216-236` fallback), plus Orin metadata extraction. No spec, ledger, or (as far as checked) ToS documents this. The new attorney-referral tables were also created **without RLS** (20260813 migration), so the moment that migration is applied, intake PII becomes anon-key-readable.

5. **The UPL wall is not uniformly enforced.** Criminal Procedure and Discovery Motion streaming **success** paths emit no server-injected disclaimer — the canonical disclaimer appears only on error paths; success relies on the LLM writing a `disclaimer` field inside its own JSON (`agents/criminal_procedure.py:150-206`, `agents/discovery_motion.py:175-210`). The attorney-referral router sits entirely outside `core/upl.py` (no `apply_disclaimer` anywhere in it). This is the documented "U1" defect from SPEC_LEDGER §2 — still unfixed for 2 of 4 named modules, and newly reintroduced in the newest feature.

### What the last 37 commits (2026-08-04 → 08-13) changed, undocumented anywhere

Attorney referral intake + user profiles; find-legal-help static directory; citation treatment ("still good law?"); corpus expansion 759 → **425,850** opinions (confirmed live by row count) with ILIKE fallback + trgm index; forms catalog audit phases 1–4 (prod now 426 published / 230 review / 30 rejected / 6 stale); Terms of Service doc. None of these have a SPEC_LEDGER row — the ledger's own Change Protocol (§6) was not followed even once.

---

## 2. OUT OF SCOPE — UNMERGED BRANCHES, NOT AUDITED

Per instruction, listed only; contents not analyzed.

| Branch | Last commit date |
|---|---|
| `chore/dep-security-bumps` (local) | 2026-08-04 |
| `chore/dep-security-bumps-2` (local + remote) | 2026-08-04 |
| `docs/integration-plan-p2-status` (local) | 2026-07-23 |
| `fix/pc-upl-stale-tests` (local + remote) | 2026-07-27 |
| `origin/fix/extract-hallucinated-date-49` | 2026-07-27 |
| `origin/railway/code-change-ogyKrA` | 2026-07-22 |
| `origin/refactor/2026-08-03` | 2026-08-03 |
| `origin/refactor/2026-08-05` | 2026-08-05 |
| `origin/refactor/2026-08-12` | 2026-08-12 |
| `origin/refactor/2026-08-13` | 2026-08-13 |
| `origin/ux/case-law-humanization` | 2026-08-11 |

---

## 3. TRACEABILITY MATRIX

Sources of promise: SL = SPEC_LEDGER.md, IP = INTEGRATION_PLAN.md, VL = phases/V2_LEDGER.md, ST = STATUS.md, RM = README.md, GH = git history (commit SHA). "Prod DB" = read-only row-count/existence check against Supabase `miedifclpqewnixxkahs` on 2026-08-13.

"Reachable in UI" asserted only where the chain route→component→nav link was traced in `frontend/src/App.tsx` + `pages/HomeHub.tsx:31-42` (12 tiles) or an in-page link.

| # | Promised capability | Source | Backend code | DB schema | API route | Frontend calls it | Reachable in UI | Tests | Status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Document upload + ingestion (PDF/OCR) | ST v1 P02, RM | `ingestion/`, `routes.py:257` | `sessions`/`documents` (45 rows prod) | `POST /upload` | `UploadFlow.jsx` | ✓ tile `HomeHub.tsx:38` | ingestion covered in unit suite | **WORKING** |
| 2 | Document triage classifier | VL P5, SL | `triage/classify.py`, `agents/classifier.py` | n/a | inline in `/upload`; also `/api/triage/*` | inline path only; triage router 0 consumers | via Upload | `test_triage_router.py` | **WORKING** (inline); triage router itself CODED_NOT_WIRED |
| 3 | Deadline engine (LLM extract → deterministic compute) | VL P4, RM, CLAUDE.md | `deadline/{extract,compute,rules,pipeline}.py` | `trigger_events`, `deadlines` — **0 rows prod** | `POST /api/deadline/analyze/{id}` (key-gated), GETs open | `ResultsPage.jsx:15,67` compute-on-demand | ✓ via Upload→Results | `test_deadline_compute.py`, eval 34/34 fatal | **PARTIAL** — fully coded+wired+tested; zero evidence of any production execution ever |
| 4 | Reminder & notification scheduler | VL P6 "COMPLETE" | `core/reminders.py`, `notifications.py`, `routers/reminders.py:29` | `deadline_reminders` 0 rows, `push_tokens` 0 rows | `POST /api/reminders/process` (key-gated) | none (server cron by design) | n/a headless | `test_reminders.py`, `test_notifications.py` | **CODED_NOT_WIRED** — pg_cron caller unconfigured (VL open gap #6); email = honest stub (`notifications.py:68-105`); nothing to remind (0 deadlines) |
| 5 | Explainer + risk scan + form guide pipeline | ST v1 P04-06 | `agents/{explainer,risk_scanner,form_guide}.py`, `routes.py:307` | `documents.classification/explanation/...` | `POST /process/{session_id}` | `UploadFlow.jsx` | ✓ | unit suite | **WORKING** (but see #6 form_guide data source) |
| 6 | Form Guide reads real form catalog | SL §3 row 4 | `agents/form_guide.py:38-49` loads `data/forms_library.json` (~6 entries, 2026-05-14) | `court_forms` 692 rows ignored by this agent | — | — | — | — | **PARTIAL** — SL §3 drift claim confirmed still true: Phase 10 ingest never reached FormGuideAgent |
| 7 | UPL wall + escalation on every output | VL P8, CLAUDE.md | `core/upl.py`, `core/escalation.py` | n/a | applied per-router | n/a | n/a | `test_upl.py`, `test_pc_upl.py` | **PARTIAL** — U1 persists: criminal + discovery streaming success paths emit no canonical disclaimer; attorney_referral router entirely outside the wall |
| 8 | Small Claims explainer + filing wizard | ST P16, IP #6/#13 | `agents/small_claims.py`, router | n/a | `/api/small-claims/{explain,generate}` (rate-limited, no auth) | `SmallClaimsExplainer.tsx` (input form + explicit submit, `:362`) | ✓ tile | `test_phase_16.py` (CI-excluded, server-dep) | **WORKING** — IP's HOLLOW/auto-fire/hardcoded-key defects all fixed |
| 9 | Criminal Procedure explainer | SL §2 | `agents/criminal_procedure.py` | n/a | `/api/criminal/explain` (rate-limited, no auth) | `CriminalProcedureExplainer.tsx` explicit submit `:439` | ✓ tile | none unit-level | **WORKING** with U1 disclaimer gap (S3-2) |
| 10 | Discovery Motion analyzer | SL §2 | `agents/discovery_motion.py` | n/a | `/api/discovery/analyze` | `DiscoveryMotionAnalyzer.tsx` | ✓ tile | none unit-level | **WORKING** with U1 gap + silent risk-parse swallow (`discovery_motion.py:209-210`) |
| 11 | Property & Casualty explainer + statutory deadlines | SL §8 | `agents/property_casualty.py` (deadline calls at `:207-208`) | n/a | `/api/property-casualty/explain` | `PropertyCasualtyExplainer.tsx` | ✓ tile | `test_pc_deadlines.py`, `test_pc_upl.py` | **WORKING** (reference implementation; success-path disclaimer via `apply_disclaimer` at `:379-380`) |
| 12 | Wills & Trusts explainer | SL §2 | `agents/wills_trusts.py` (disclaimer chunk `:183`) | n/a | `/api/wills-trusts/explain` | `WillsTrustsExplainer.tsx` | ✓ tile | none unit-level | **WORKING** |
| 13 | Police Report Analyzer v2 + opinion retrieval | VL P9 + opinion section | `agents/police_report_v2.py`, `services/opinion_retrieval.py` | `legal_opinions` 425,850 rows (verified) | `/api/police-report/analyze` | `PoliceReportAnalyzer.tsx` + `sseMerge.ts` | ✓ tile | `test_opinion_mapper.py`, `sseMerge.test.ts` (5) | **WORKING** |
| 14 | Police report legacy batch analyze | SL §3 row 1 | `agents/scanner.py` v1 | n/a | `/api/police-report/analyze/batch` (`police_report.py:70`) | **no frontend caller** (grep: none) | ✗ | — | **CODED_NOT_WIRED** (known; SL says migrate-then-delete — never done) |
| 15 | FL Case Law Lookup | ST P22, IP #12 | `routers/case_law.py` (corpus-only, **no LLM** — SL §4 row for `case_law.py:72` is stale) | `legal_opinions` | `/api/case-law/search` (no auth, no rate limit — DB-only) | `CaseLawLookupFL.tsx` | ✓ tile ("Search 425,850 Florida opinions" — count **verified true**) | `test_phase_22.py` (CI-excluded) | **WORKING** |
| 16 | Citation treatment ("still good law?") | GH `2d63889`, `bfaa7c8` | `case_law.py:202-227` `_fetch_treatments` | `citation_treatment` exists in prod, **0 rows** | rides `/api/case-law/search` | case-law UI renders treatment | ✓ | none | **CODED_NOT_WIRED** — extractor scripts never populated prod; feature silently shows nothing |
| 17 | Orin 443K raw opinion search | VL "Orin" memory, `orin_opinions.py` docstring | `services/orin_opinions.py` — `ssh joe@100.117.93.67` via subprocess (`:278-287`) | Orin box (not Supabase) | last-resort fallback in `opinion_retrieval.py:194-202` | indirect | n/a | none | **PARTIAL** — works only where Joe's SSH key + Tailscale exist; on Railway fails every time → silent `[]` (`orin_opinions.py:337-345`). Largely superseded by the 425K Supabase corpus |
| 18 | Forms Finder (search/facets/download) | VL P2/P10, IP #5 | `routers/forms.py` | `court_forms` 692 rows: 426 published / 230 review / 30 rejected / 6 stale | `/api/forms/*` | `FormsFinderFL.tsx` | ✓ tile | `test_phase_19.py`, `test_form_recommender.py` | **WORKING** — stale/withdrawn gated (`forms.py:602,617`) per CLAUDE.md constraint |
| 19 | Forms AI suggest | VL P10 | `forms.py:503` (`SUGGEST_MODEL` sonnet) | same | `POST /api/forms/suggest` (no auth, **no rate limit**, LLM) | FormsFinderFL | ✓ | — | **WORKING** (cost-exposure caveat §4.6) |
| 20 | Expungement quiz + packet | ST P17, IP #9 | `routers/expungement.py:56` hardcoded JSON rules + phantom TODO `:58`; `agents/expungement.py` LLM agent used only by legacy paths | n/a | `/api/expungement/{eligibility,generate}` (no auth/limit) | `ExpungementFL.tsx:23` | ✓ tile | `test_phase_17.py` (CI-excluded) | **WORKING** (deterministic path) — SL §3 row 2 duplicate-impl drift still unresolved |
| 21 | Landlord/Tenant 3 sub-flows | ST P18, IP #10 | `routers/landlord.py:86-96` | n/a | 3 × `/generate` (no auth/limit) | `LandlordTenantFL.tsx` | ✓ tile | `test_phase_18.py` (CI-excluded) | **WORKING** |
| 22 | Traffic wizard | ST P20, IP #11 | `routers/traffic.py:37` | n/a | `/api/traffic/generate` | `TrafficFL.tsx` | ✓ tile | `test_phase_20.py` (CI-excluded) | **WORKING** |
| 23 | Filing Packet — $35 Stripe | CLAUDE.md, ST P23 | `routers/packet.py`, `services/packet_builder.py` | `packets` 31 rows prod | `/api/packet/*` | `FilingPacket.tsx` | ✓ from generate flows | `test_phase_23.py` (CI-excluded) | **PARTIAL** — fully coded, but `PAYMENTS_ENABLED` defaults false (everything free); open unauthenticated `POST /{packet_id}/mark_paid` bypass (`packet.py:163`) |
| 24 | Chat Expert drawer (5 free msgs then paywall) | VL post-v2, IP #17 | `agents/chat_expert.py` (canonical disclaimer template), `routers/chat.py:57` | n/a | `POST /api/chat/{module}` (**no auth, no rate limit**, LLM) | ChatDrawer on module pages | ✓ drawer | none unit-level | **WORKING** — paywall count derived from client-supplied `chat_history` (`chat.py:68-70`) = trivially resettable (moot while payments off) |
| 25 | AI intake router (HomeHub) | SL §2 row 1 | `routers/intake.py:127` (Haiku) | n/a | `POST /api/intake` (no auth/limit) | `HomeHub.tsx:292` | ✓ home page | none | **WORKING** — errors still swallowed to 200/`unknown` (`intake.py:196-200`); SL's reconcile recommendation unaddressed |
| 26 | Attorney referral intake (AI chat + profile + submit) | GH `ff667da` (2026-08-06) | `routers/attorney_referral.py` | `user_profiles`/`attorney_inquiries` — **missing in prod (404)**; migration 20260813 has **no RLS** | 4 routes (no auth, no rate limit) | `AttorneyReferralFL.tsx` | **✗ no nav link anywhere** (only App.tsx:92 route) | none | **PHANTOM** (in prod) — chat turn works, but profile save + submit hit nonexistent tables; unreachable in UI regardless |
| 27 | Find Legal Help directory | GH `bb5f6aa` | frontend-only: static `fl_legal_aid_providers.json` + `fl_public_defenders.json` | n/a | none | self-contained | **✗ no nav link** (only App.tsx:93 route) | none | **WIRED_NOT_REACHABLE** |
| 28 | Law corpus API (statutes/rules/AOs/closures) | VL P3 | `routers/law.py` | statutes 882 ✓ (matches claim), court_rules 323 ✓, LAOs 12, closures **9** | `/api/law/*` (no auth — public reference data) | none (internal by design) | n/a HEADLESS-intentional | — | **WORKING** (headless by design) — but see closures drift, §4.8 |
| 29 | All-20-circuits court closures seeded (99 entries) | VL 2026-08-08 improvement C "MERGED" | migration `20260808000000` in repo | **prod has only the 9 statewide holidays** (verified rows) | — | — | — | — | **PHANTOM in prod** — migration never applied |
| 30 | PII redaction | VL P1 | `ingestion/pii_redactor.py`, wired at `routes.py:363` | n/a | inside `/process` | n/a | n/a | `test_pii_redactor.py` (21) | **WORKING** |
| 31 | Eval harness + launch gate | VL P7 | `evals/run_all.py` | locked `ground_truth.json` — git history: single creating commit `714b054`, never edited | CI `eval-deadline.yml` | n/a | ran live: **34/34 fatal PASS** | — | **WORKING** |
| 32 | Reminder email delivery (Resend) | memory/VL open gap | `notifications.py:68-105` — returns False always; `TODO(email)` `:98` | n/a | — | — | — | `test_notifications.py` | **MISSING** (honest stub, correctly documented as such) |
| 33 | React Native (Expo) mobile app | ST v1 P13 "✅ DEPLOYED" | **`mobile/` is empty** (0 files) | push_tokens 0 rows | `/user/*/push-token` exists | n/a | n/a | none | **PHANTOM** — STATUS.md claims DEPLOYED; nothing exists |
| 34 | Compliance framework | `routes.py:126-141` gating | `compliance/` package (own pyproject) | n/a | `/compliance/*` mounted only if importable | none | ✗ | own tests dir | **CODED_NOT_WIRED** — not in `requirements.txt`, so never installed on Railway; router never mounts in prod |
| 35 | ES (Spanish) i18n end-to-end | CLAUDE.md, VL | `core/i18n`, disclaimers EN/ES; opinion corpus EN-only w/ honesty stamp (SL §7) | n/a | `language` params present | `react-i18next` | partially | some | **PARTIAL / UNVERIFIED** — plumbing exists everywhere checked; no end-to-end ES verification performed in this audit |
| 36 | Top-level `POST /eligibility` | IP #22 "DARK — delete" | `routes.py:165` — LLM-backed (`expungement.check_eligibility`), **no auth, no rate limit** | n/a | yes | only dead `ExpungementPage.jsx:44` (unrouted) | ✗ | — | **CODED_NOT_WIRED** — dead endpoint + dead caller pair, both still present; now also an open LLM cost surface |

**UNDOCUMENTED (exists in code, promised nowhere):** (a) top-level `src/content/property-casualty/*.mdx` — 13 content files referenced by nothing found; (b) `PC_DEADLINE_DIAGNOSIS.md`-era debug helpers under `scripts/` (citation treatment extractor, debug scripts `e3c7a82`) with no spec/ledger entry.

---

## 4. FAILURE-CLASS FINDINGS

### 4.1 Orphaned backend routes (endpoint defined, no frontend caller)

| Route | File:line | Note |
|---|---|---|
| `POST /api/police-report/analyze/batch` | `routers/police_report.py:70` | v1 scanner path; V2_LEDGER itself calls it dead |
| `POST /api/triage/classify\|confirm` | `routers/triage.py:16,92` | `/upload` classifies inline instead; 0 consumers |
| `GET/POST /api/analyze/*` | `routers/analysis.py:33,75` | 0 consumers **and broken** (see 4.12) |
| `POST /eligibility` (top-level) | `routes.py:165` | only caller is unrouted `ExpungementPage.jsx` |
| `POST /user`, `GET /user/{id}`, `/user/{id}/push-token`, `POST /subscribe/{user_id}` | `routes.py:239-255` | mobile/subscription era; no web caller found |
| `GET /api/packet/walkthrough` | `packet.py:117` | no frontend caller found (UNVERIFIED — may be used by packet page indirectly) |

### 4.2 Orphaned frontend calls (fetch to path that fails in prod)

- `AttorneyReferralFL.tsx` → `/api/attorney-referral/users` + `/submit` → **tables missing in prod** → Supabase APIError → HTTP 500. The page will half-work (chat turns) then fail at save/submit.
- `ExpungementPage.jsx:44` → `/eligibility` — dead caller (component unrouted), pairs with 4.1.

### 4.3 Unrouted components (dead code, still in tree)

`pages/AnalysisDashboard.jsx`, `pages/LandingPage.jsx`, `pages/ExpungementPage.jsx`, `pages/PhaseStub.tsx`, `components/layout/Navbar.jsx` — zero importers (verified by grep). IP P2.1.c promised their deletion; not done.

### 4.4 Dead navigation

- None found pointing at nonexistent routes (`/upgrade` link from `ChatDrawer` is gone — fixed since IP).
- **Inverse problem:** two routed pages have no inbound nav from any live surface: `/attorney-referral` (App.tsx:92) and `/find-legal-help` (App.tsx:93). Not in `MODULE_TILES` (HomeHub.tsx:31-42), not in SiteHeader (logo-only), not linked from any page (repo-wide grep).

### 4.5 Silent degradation (missing config → empty result instead of error)

| Site | Behavior when dependency absent |
|---|---|
| `memory/db.py:10-21` + **20 `if self.client is None` guards** | No Supabase creds → every DB method returns `{}`/`None`/`[]`/no-op. A misconfigured prod backend serves empty data instead of failing startup |
| `config.py` (whole file) | No env var is required; every setting defaults (`""`, `testkey123`, `false`). Nothing validates at startup |
| `services/opinion_retrieval.py:210-212` | Any retrieval failure → `[]` (by design, logged) |
| `services/orin_opinions.py:337-345` | SSH/psql unreachable (always, on Railway) → `[]` |
| `deadline/pipeline.py:99-112` | `court_closures` fetch failure → logged, **computation proceeds without closures** — a computed deadline can silently land on a court-closed day |
| `routers/intake.py:196-200` | Both LLM attempts fail → HTTP 200 with `module="unknown"`; client can't distinguish outage from ambiguity |
| `notifications.py:68-105` | Email honest-stub — logs + returns False (intentional, well-documented) |
| `case_law.py:202-227` | `citation_treatment` empty/erroring → treatment silently absent (currently the permanent prod state) |

### 4.6 Feature flags / effective values

| Flag | Read at | Default | .env.example | Effective prod value |
|---|---|---|---|---|
| `PAYMENTS_ENABLED` | `config.py:36-38`; gates webhook (`routes.py:172`), subscribe (`:251`), filing count (`:423`), packet checkout (`packet.py:55`), chat limit | `false` | `false` | **UNVERIFIED** (Railway env not readable from repo). If false: $35 product effectively free — CLAUDE.md's "Stripe product $35" is aspirational |
| `EMAIL_PROVIDER` | `notifications.py:90` | `""` = delivery disabled | `""` | reminders cannot email |
| `COURTLISTENER_TOKEN` | `case_law.py:128` | `""` = CL fallback off | absent from .env.example | corpus-only |
| `MESSAGING_PLATFORM` | `config.py:45` | `"log"` | absent | push presumably logs only |
| compliance router | `routes.py:126-141` | mounts only if package importable | n/a | never mounts on Railway (not in requirements.txt) |
| **Gap:** `DEEPSEEK_API_KEY`, `COURTLISTENER_TOKEN`, `MESSAGING_PLATFORM`, `BACKEND_PORT`, `FRONTEND_URL` are read by code but **missing from `.env.example`** — contradicts CLAUDE.md's "all required env var names" claim | | | | |

### 4.7 Swallowed exceptions

- 112 `except Exception` sites across backend src (most log and degrade — pattern, not individual bugs).
- `except`-then-`pass` (4): `agents/property_casualty.py:381`, `agents/discovery_motion.py:209` (drops the entire deterministic risk-score event on parse failure — user gets analysis with no risk score and no error), `core/json_utils.py:40` (fallback chain, acceptable), `core/upl.py:216` (date-parse in escalation check — a malformed date silently skips a fatal-deadline escalation trigger).
- Ruff config (`e3f0e34`) suppresses BLE001 globally as "intentional bare excepts with loggers" — accurate for the sites sampled, but it also mutes the lint that would catch future silent swallows.

### 4.8 Schema drift (repo ⇄ prod, verified live)

| Object | Repo | Prod | Consequence |
|---|---|---|---|
| `user_profiles`, `attorney_inquiries` | migration 20260813 | **404 — missing** | attorney-referral save/submit broken |
| `filings` | migration 20260704 | **404 — missing** | `db.count_filings` → error path; `/florida-filing/prepare` free-count gate silently degraded |
| circuit closures seed (~90 rows, 2026–27) | migration 20260808 | **not applied** (9 statewide rows only, created 2026-05-19) | circuit-specific deadline adjustments impossible |
| `citation_treatment` | migration 20260812 | exists, **0 rows** | feature ships UI with no data behind it |
| `legal_opinions` | migration 20260703 (759-era) | **425,850 rows** | corpus grew 560× via out-of-band ingestion — no migration/script in repo records how prod got these rows |
| `billing_events` | claimed in STATUS.md "v2 tables" | never in any migration, never in code | pure documentation fiction |
| `deadlines`/`trigger_events`/`deadline_reminders`/`push_tokens` | full schema + RLS | exist, **0 rows ever** | core pipeline never executed in prod |
| RLS | all Phase-1 tables have policies | `documents` verified: anon sees 0/45 ✓ | `user_profiles`/`attorney_inquiries`/`citation_treatment` migrations contain **no RLS** (`citation_treatment` confirmed anon-readable in prod, harmless today because public-ish data + 0 rows; the other two become a PII leak the day their migration is applied) |

### 4.9 Auth & tenancy gaps

| Gap | Where | Severity driver |
|---|---|---|
| Server-side `API_KEY` default `"testkey123"` | `config.py:30` | if Railway unset, all "protected" endpoints are open with a public string |
| Shared static key in JS bundle | `api.js:11` + 6 pages (`VITE_API_KEY`) | key is public by definition; architectural, known since IP A2 |
| `GET /api/deadline/{document_id}/deadlines` + `/trigger-events` | `deadline.py:43,62` | **no auth of any kind**; any document_id → that user's legal deadlines |
| `GET /document/{id}`, `GET /documents/{user_id}`, `POST /chat/{id}` | `routes.py:389-419` | key-gated but zero ownership check → any key holder reads anyone's docs/chats (IDOR; SL flagged this 2026-06-30, unchanged) |
| `GET /api/attorney-referral/users/{user_id}` | `attorney_referral.py:128` | no auth → full PII profile by UUID (latent until table exists) |
| `POST /api/attorney-referral/users` | `attorney_referral.py:88` | no auth; upsert keyed by client-supplied email → anyone can overwrite any profile |
| `POST /api/packet/{packet_id}/mark_paid` | `packet.py:163` | unauthenticated payment bypass (moot while payments off) |
| Unauthenticated LLM endpoints with **no rate limit** | `/api/chat/{module}` (`chat.py:57`), `/api/intake` (`intake.py:127`), `/api/forms/suggest` (`forms.py:503`), `/api/attorney-referral/intake` (`attorney_referral.py:138`), top-level `/eligibility` (`routes.py:165`), `/api/expungement/*`, `/api/landlord/*`, `/api/traffic/*` (`traffic.py:37`) | open cost exposure; the 10/min limiter covers only the 8 explainer/analyzer routes |
| Delete is correctly scoped | `routes.py:227-238` (`delete_document` requires session ownership) | positive control — proves the pattern exists and wasn't applied elsewhere |

### 4.10 Broken async/streaming contracts

- **Criminal/Discovery stream shape:** server yields raw LLM-JSON text chunks interleaved with complete typed JSON events (`relevant_opinions`, error payloads). Client (`CriminalProcedureExplainer.tsx:385-410`) distinguishes by attempting `JSON.parse` per chunk — an **error event that is valid JSON but lacks `type`** falls through and is concatenated into the accumulating explanation JSON, corrupting the final parse ("Could not parse the explanation"). Edge case, not the common path.
- Police report path has a tested pure reducer (`sseMerge.ts` + 5 vitest tests) — the one solid contract.
- `analysis.py:33-75`: `await db.get_document(...)` on a **sync** method (`db.py:205`) → TypeError; `EscalationRouter.evaluate` does not exist (`escalation.py:59` defines `route`) → these endpoints 500 on every invocation. Dead + broken (0 consumers).

### 4.11 Hardcoded secrets / refs / URLs

- **No live secrets found in source** (gitleaks also runs in CI). `.env` files untracked.
- `testkey123` as server default (`config.py:30`) — a known-public credential in code.
- Hardcoded infra coupling: `ssh joe@100.117.93.67` + `psql -U joe -d legal_clear` (`orin_opinions.py:10-12,278-287`) — personal dev box wired into a production code path.
- Supabase project ref + Railway URLs appear in docs/CORS config (acceptable; not secrets).

### 4.12 Stubs presented as done

- Email delivery: honest stub, honestly labeled (`notifications.py`) — the *docs* (V2_LEDGER P6 "COMPLETE") oversell it.
- Expungement `/eligibility`: hardcoded JSON substring matching presented as the product's eligibility check; TODO references a phantom "Phase 07 … v1.1" (`expungement.py:58`).
- Citation treatment: fully-built UI + query path over a permanently-empty prod table — functionally a stub in production.
- STATUS.md "React Native (Expo) ✅ DEPLOYED" over an empty directory — the starkest stub-as-done.

### 4.13 Dependency reality

- `requirements.txt` ⇄ `pyproject.toml`: **in sync** (name-level diff clean).
- `compliance/` has its own pyproject; nothing installs it in prod (see 4.6).
- Frontend `package.json`: not exhaustively cross-checked (LOW priority; `npm run build` + vitest pass).
- Orin path requires `ssh` binary + key at runtime — an undeclared system dependency no manifest captures.

### 4.14 Test theater

- CI (`pytest.yml:50-60`) excludes 10 server-dependent files — **documented and reasonable**, but it means the 9 `test_phase_*` E2E suites run nowhere automatically; a `pytest.mark.integration` TODO sits unimplemented in the workflow header.
- CI-scope suite run live for this audit: **196 passed, 1 skipped, 4.69s** — healthy, real assertions spot-checked.
- `evals/ground_truth.json`: single creating commit (`714b054`), never edited — lock respected.
- Eval CI runs fast mode only (no LLM) — extraction quality is guarded only by manual `--full` runs (last recorded 2026-06-29, VL gap #9).
- `test_opinion_retrieval_integration.py` silently hits **production Supabase** when `backend/.env` is present (it did during this audit) — a unit-suite test with a live prod dependency.
- Frontend: exactly 1 test file (sseMerge). Everything else untested.

---

## 5. DOCUMENT ASSESSMENT

### 5.1 SPEC_LEDGER.md

**False or unsupported claims (vs 0c2e006 + prod):**
1. Header: "Last fully re-verified against source: 2026-06-30" — sections self-date to 07-05; nothing covers the 37 commits since 08-04. The document is 5+ weeks stale against a repo that added 4 features.
2. §1 registration line numbers (`reg :72` … `:90`) — actual registrations are `routes.py:106-125`. Every row's anchor is wrong.
3. §1 has **no row** for Attorney Referral (registered `routes.py:123`) — a module exists that the "canonical mapping of every router" omits.
4. §4 model registry: `routers/case_law.py:72 | claude-sonnet-4-6` — false; case_law contains **no LLM call** (rewritten corpus-only). Registry also omits `attorney_referral.py:199` (haiku-4-5) and three `deepseek-chat` call-sites (`attorney_referral.py:224`, `opinion_retrieval.py:262`, `orin_opinions.py:178`) — a whole third-party provider absent from the "every LLM call-site" table.
5. §1 drift note "Packet = $35 paywall disabled in code (contradicts CLAUDE.md)" — stale framing; it is now governed by the documented `PAYMENTS_ENABLED` switch.
6. §7 "759-opinion Supabase corpus" — prod holds 425,850 rows; the corpus story changed completely with no ledger update.
7. §7 backend-suite scope note (43 failed / 121 passed) — stale; current CI-scope result is 196/0.
8. §6 Change Protocol — presented as enforceable; **violated by every subsequent feature commit** (no new rows, no re-verification dates). A protocol nothing follows is a false claim about how the repo works.

**True-and-still-open claims it deserves credit for:** U1 (criminal/discovery) still real; intake bypass/swallow still real; expungement duplicate-impl still real; form_guide JSON loader still real; IDOR on document lookups still real; Haiku deviations still undocumented.

**Implemented capabilities it omits:** attorney referral, find-legal-help, citation treatment, ILIKE/trgm 425K search, forms catalog audit + `rejected`/`stale` statuses, ToS doc.

**Structural problems:** no per-claim owner; no semantic versioning of the doc itself; "Last verified" exists per-row but was never updated post-06-30; no link from claim → commit SHA; status vocabulary (MINOR/MAJOR) undefined in measurable terms; no machine-checkable assertions (every claim requires a human re-audit — which is why it rotted in 5 weeks).

**What production-grade would add:** per-row `verified_at` + commit SHA; a `VERIFY` script asserting mechanical claims (route exists, model string matches, table exists **in prod**, row has RLS); explicit not-built/deferred/rejected sections; a CI job that fails when a router/agent/LLM call-site exists without a ledger row (greppable — this is automatable); DeepSeek/third-party processor registry.

### 5.2 INTEGRATION_PLAN.md

**Claims now false (because the work was done — the doc was never closed out):**
1. "Small Claims … HOLLOW / auto-fire / hardcoded key" — all three fixed (`SmallClaimsExplainer.tsx:305` comment cites P2.0-B; explicit submit at `:362`; no testkey literal anywhere in frontend).
2. Same for Criminal Procedure (P2.0.c) — fixed.
3. "7 files ship testkey123" (A2) — zero files do now. The **server-side default** persists, which the plan never flagged.
4. "allow_origins=[\"*\"]" — tightened to two origins (`routes.py:32-35`).
5. Feature table rows 8–12 "ORPHANED" (Upload, Expungement, Landlord, Traffic, Case Law) — all five have HomeHub tiles now (P2.1 executed).
6. "`/upgrade` … not a routed page" — link no longer exists.

**Claims still true:** dead components list (all 5 still present — P2.1.c's deletion half never happened); triage/analysis routers still ambiguous/dead; top-level `/eligibility` still undeleted; headless law/reminders unchanged.

**Omissions:** everything post-07-06 (four features); the plan has no concept of prod-schema verification, which is where the real breakage is.

**Structural problems:** point-in-time audit frozen as a plan — no completion tracking, so done items read as open defects and the doc now actively misleads; no owner; no dates on execution; acceptance criteria are live-browser manual checks nobody recorded performing; "CONFIRMED STATE (do not re-litigate)" section enshrines findings that later changed.

**What production-grade would add:** per-item status/date/PR link; separation of "audit snapshot" (immutable, dated) from "plan" (living, checked off); acceptance evidence links; a rule that closing a P2.x item requires updating the doc in the same PR.

### 5.3 Collateral documents (context, briefer)

- **STATUS.md**: claims React Native DEPLOYED (empty dir), `billing_events` table (never existed), duplicate/conflicting numbering in its own open-items table (#8-#10 appear twice), form counts stale (443 vs prod 426 published).
- **V2_LEDGER.md**: improvement C "99 closure entries … MERGED" — merged to git, never applied to prod; P6 "COMPLETE" overstates a stub-backed reminder system; "Refactor agent re-enabled (cron …)" describes infrastructure outside the repo.
- **README.md**: v2 badge says "in progress" while V2_LEDGER/STATUS say all complete — pick one.

---

## 6. TRIAGE LIST

Severity per the agreed scale. **Blast radius** = what could break if fixed carelessly. **Indep** = can be done standalone.

### S1 — data loss / security / tenancy / secrets

| ID | What | Where | Why it matters | Proposed fix | Blast radius | Indep? |
|---|---|---|---|---|---|---|
| S1-1 | `API_KEY` server default `"testkey123"` | `config.py:30` | If Railway env lacks `API_KEY`, every "protected" endpoint accepts a public string. Cannot be verified from repo — must check Railway | Remove default; fail startup if unset in non-development; verify Railway value + rotate | Startup behavior change; dev envs need .env update | Yes |
| S1-2 | New PII tables created without RLS | `supabase/migrations/20260813000000` (`user_profiles`, `attorney_inquiries`); also `citation_treatment` (20260812) | The moment the migration is applied to prod, intake PII (names, phones, case narratives) is anon-key readable via PostgREST | Amend/append migration: enable RLS on all three, service-role-only (no policies), matching `legal_opinions` pattern | None today (tables absent in prod); must land **before** S2-1 applies the migration | Yes — **prerequisite of S2-1** |
| S1-3 | Unauthenticated PII read + unauthenticated upsert-by-email | `attorney_referral.py:88-135` | Any UUID → full profile; any email → overwrite profile | Require auth or at minimum a per-session token; never upsert on client-supplied email without verification | Attorney-referral frontend flow | Yes |
| S1-4 | IDOR: deadline GETs (no auth at all); `/document`, `/documents/{user_id}`, `/chat/{id}` (shared key, no ownership) | `deadline.py:43,62`; `routes.py:389-419` | Anyone (or any key holder) reads any user's legal situation | Session-scope like `delete_document` (`routes.py:227`) already does | ResultsPage must pass session identity | Yes |
| S1-5 | User legal data sent to DeepSeek (3 call-sites) undisclosed | `opinion_retrieval.py:246+`, `attorney_referral.py:224`, `orin_opinions.py:178` | Third-party, non-US processing of legal PII; ToS/privacy alignment unknown | Product decision: drop, or gate + disclose in ToS; document in ledger either way | Attorney-question enrichment quality | Needs Joe's call (Q4) |
| S1-6 | Unauthenticated payment bypass endpoint | `packet.py:163` (`mark_paid_dev`) | Defeats Stripe the day `PAYMENTS_ENABLED=true` | Gate behind webhook-verified flow or key + dev-env check | Post-checkout redirect UX | Yes |

### S3 — silent failures hiding S1/S2 (fix before S2, per your ordering)

| ID | What | Where | Why | Fix | Blast radius | Indep? |
|---|---|---|---|---|---|---|
| S3-1 | Migration application to prod is unverified and patchy | process gap; evidence in §4.8 | The repo cannot know what schema prod has; caused S2-1/S2-3/S2-4 invisibly | Add a mechanical schema-parity check (script comparing migrations to prod information_schema via service key) run in CI or a VERIFY target; reconcile current drift explicitly | None (read-only check) | Yes — **prerequisite of all S2 schema items** |
| S3-2 | U1: no canonical disclaimer on criminal/discovery streaming success; attorney_referral outside UPL wall | `criminal_procedure.py:150-206`, `discovery_motion.py:175-210`, `attorney_referral.py` (whole) | Core legal-safety invariant silently unenforced | Emit server-side disclaimer terminal event (copy wills_trusts `:183` or PC `:379` pattern); wrap referral responses in `apply_disclaimer` | Client parsers must tolerate the extra event (police-report pattern shows how) | Yes |
| S3-3 | No startup config validation anywhere | `config.py` | Missing SUPABASE/ANTHROPIC creds → degraded-mode empty product (20 guard sites) instead of a crash; your stated rule: "config that is missing must raise loudly" | Startup validator: required vars fatal outside `ENVIRONMENT=development` | Local dev ergonomics; degraded-mode tests | Yes |
| S3-4 | Deadline computed without closures on fetch failure | `pipeline.py:99-112` | A silently-wrong legal deadline is the product's worst-case failure | Escalate/refuse computation (or mark assumption_disclosure) when closure fetch fails | Deadline pipeline tests | Yes |
| S3-5 | Intake failure → 200 `unknown`; discovery risk-parse → silent pass; upl date-parse → silent pass | `intake.py:196`, `discovery_motion.py:209`, `upl.py:216` | Outages indistinguishable from valid results; a malformed date can skip a fatal-deadline escalation | Distinguish error payloads; log at error + emit error event; upl: treat unparseable date as escalate-worthy | Small client handling changes | Yes |

### S2 — user-facing feature promised and broken/unreachable

| ID | What | Where | Why | Fix | Blast radius | Indep? |
|---|---|---|---|---|---|---|
| S2-1 | Attorney referral broken in prod (missing tables) and unreachable (no nav) | migration 20260813 unapplied; no HomeHub tile/link | Shipped feature (commit `ff667da`) cannot complete, invisibly | Apply migration **after S1-2**; add nav entry; add error surfacing on save failure | New live feature exposure | Prereqs: S1-2, S1-3, S3-1 |
| S2-2 | Find Legal Help unreachable | no inbound link to `/find-legal-help` | Built, routed, invisible | HomeHub tile or footer link | trivial | Yes |
| S2-3 | Circuit court-closure data absent in prod | migration 20260808 unapplied | Deadline correctness for circuit-specific closures impossible; compounds S3-4 | Apply seed after S3-1 parity check | none | Prereq: S3-1 |
| S2-4 | Citation treatment: empty prod table behind live UI | `citation_treatment` 0 rows; extractor scripts in `scripts/` | "Still good law?" indicator silently never appears — worse, absence may read as "no negative treatment" (a legal-information hazard) | Run extractor against prod, or hide the UI until data exists; decide which | case-law UI | Prereq: S3-1; needs Joe's call (Q5) |
| S2-5 | Deadline/reminder subsystem has never run in prod (0 rows across 4 tables) + pg_cron caller unconfigured + email stub | §4.8; VL open gaps 6 | The core product promise is unexercised in production; unknown whether it *would* work (Railway env, service key, LLM key at runtime) | One supervised prod smoke test (upload → process → deadline analyze); configure pg_cron app settings; wire Resend (separate item) | prod data writes | Partially; email = own item |
| S2-6 | `/api/analyze/*` endpoints 500 on every call | `analysis.py:33-75` (`await` on sync fn; nonexistent `evaluate`) | Registered, "documented" surface that cannot work | Delete or fix; they have 0 consumers — recommend delete (with S6 batch) | none | Yes |

### S4 — correctness/reliability risks not yet user-visible

| ID | What | Where | Fix | Indep? |
|---|---|---|---|---|
| S4-1 | Unlimited unauthenticated LLM endpoints (8+ routes) | §4.9 last row | Extend `@limiter.limit` to every LLM-backed route; consider origin allowlist | Yes |
| S4-2 | Chat paywall counts client-supplied history | `chat.py:68-70` | Server-side session count (moot until payments on — pair with payments work) | Yes |
| S4-3 | SSE error-event corrupts accumulating JSON parse | `CriminalProcedureExplainer.tsx:385-410` (+ discovery twin) | Type all server events or filter `error` events in client | Yes |
| S4-4 | Orin SSH path in prod code (personal box, hardcoded IP, undeclared ssh dependency) | `orin_opinions.py` | Env-gate it (`ORIN_ENABLED`) or remove now that Supabase holds 425K | Yes |
| S4-5 | Unit suite silently tests against prod Supabase when `.env` present | `test_opinion_retrieval_integration.py` | Mark as integration + skip without explicit opt-in env var | Yes |
| S4-6 | 4 undocumented Haiku pins + `claude-haiku-4-5` (unversioned alias) in referral | SL §4 + `attorney_referral.py:199` | Document as exceptions or revert — SL §4 rule already defines the norm | Yes |
| S4-7 | `.env.example` missing 5 vars code reads | §4.6 | Add them | Yes |
| S4-8 | form_guide reads 6-entry JSON instead of 692-row `court_forms` | `form_guide.py:38-49` | Rewire per SL §3 row 4 | Yes |

### S5 — documentation drift

| ID | What | Fix |
|---|---|---|
| S5-1 | SPEC_LEDGER stale/false claims (§5.1 items 1–8) | Phase 3 rebuild |
| S5-2 | INTEGRATION_PLAN never closed out; now misleads (§5.2) | Phase 3 rebuild: split immutable audit from living plan |
| S5-3 | STATUS.md phantom claims (RN app, billing_events, dup numbering) | Correct or retire in favor of ledgers |
| S5-4 | V2_LEDGER P6 "COMPLETE" + improvement C "MERGED" overstate prod reality | Annotate with prod-verified status |
| S5-5 | README v2 badge conflicts with ledgers | Align |
| S5-6 | CLAUDE.md ".env.example has all required env var names" false | Fix alongside S4-7 |

### S6 — cleanup / dead code

| ID | What |
|---|---|
| S6-1 | Delete 5 dead frontend components (§4.3) — IP P2.1.c leftovers |
| S6-2 | Delete top-level `/eligibility` + `ExpungementPage.jsx` pair |
| S6-3 | Resolve `scanner.py` v1 + `/analyze/batch` legacy path (SL §3 row 1 plan, never executed) |
| S6-4 | Delete or wire `/api/triage/*`; delete broken `/api/analyze/*` (with S2-6) |
| S6-5 | Orphaned mobile-era routes (`/user*`, `/subscribe`) — decide fate with mobile-app question (Q8) |
| S6-6 | Top-level `src/content/*.mdx` — referenced by nothing found; confirm and remove or wire |
| S6-7 | `data/forms_library.json` after S4-8 |

---

## 7. OPEN QUESTIONS FOR JOE

1. **Railway env:** Is `API_KEY` actually set in `zesty-delight` (i.e., is the `testkey123` default live in prod)? Is `PAYMENTS_ENABLED` set, and to what? Is `DEEPSEEK_API_KEY` set in prod? I cannot read Railway config from the repo.
2. **Migration process:** What do you believe applies `supabase/migrations/` to prod? Evidence says 20260812 applied but 20260704, 20260808, 20260813 did not. Was 20260812's table created manually? Until this is answered, S3-1 blocks all schema-dependent fixes.
3. **How did `legal_opinions` get 425,850 rows?** No script or migration in the repo performs that ingest. Where does the ingestion pipeline live, and is the trgm index (20260811) actually built in prod (query performance suggests yes, unverified)?
4. **DeepSeek:** intentional as a production processor of user legal data? If yes, it needs ToS/privacy disclosure + a ledger entry; if no, three call-sites need removal. This is a product/legal decision, not mine.
5. **Citation treatment:** did you intend to run `scripts/` extractors against prod before exposing the good-law UI? Empty-table-behind-live-UI is arguably worse than no feature (absence of negative treatment reads as endorsement).
6. **Attorney referral + Find Legal Help unreachable:** soft-launch on purpose (direct URL only), or was the nav tile forgotten?
7. **`deadlines` = 0 rows:** consistent with "no real users yet," or do Railway logs show `/api/deadline/analyze` attempts failing? I can't see prod logs; this distinguishes "unused" from "broken."
8. **Mobile app:** STATUS.md claims Phase 13 deployed; `mobile/` is empty. Was it built elsewhere and never committed, or abandoned? Determines fate of `/user/*` push-token routes.
9. **Orin box:** keep the SSH fallback (dev-only convenience) or remove now that the corpus lives in Supabase?
10. **Compliance package:** future workstream or graveyard? It's the only conditionally-mounted router.
11. **Intent for `/api/triage` and `/api/analyze` routers:** IP marked both "AMBIGUOUS — decide" in July; still undecided. Retire or adopt?

---

*Phase 1 complete. No fixes applied. Awaiting triage approval.*
