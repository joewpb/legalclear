# LegalClear — v2 Phase Ledger

**Single source of truth for v2 build state.**
v1 state lives in `phases/LEDGER.md`. This file tracks phases defined in
`phases/BUILD_PLAN.md` (Phases 0–N). If this ledger disagrees with the repo,
the repo wins — re-verify and correct.

Status values: `COMPLETE` · `IN PROGRESS` · `PENDING` · `BLOCKED`

---

| # | Title | Status | Date | Notes |
|---|-------|--------|------|-------|
| 0 | Stabilize the Foundation | COMPLETE | 2026-06-23 | Re-verified: 2 new PRs merged (#10 migration rename, #13 forms integration); forms/ harvest debris cleaned (167MB → 1.3MB); .gitignore hardened (forms/*.txt, forms/*/, forms/crawled/, .whale/, supabase-schema-*.svg); AGENTS.md phase count fixed (0–8 → 0–9); CLAUDE.md verified accurate; README baseline confirmed |
| 1 | Database Schema, Security & PII | COMPLETE | 2026-06-23 | Re-verified: 6 migrations intact; 9 RLS policies verified; packets uuid migration ok; pg_cron retention jobs active; PII redaction implemented (PIIRedactor class, regex-based SSN/DOB/financial/DL detection, 21 tests pass, wired into /api/process after extraction); delete endpoint exists. Remaining manual gap: anon sign-in (needs Supabase dashboard — no PAT available). Mobile dir empty (placeholder). Frontend types regenerated. |
| 2 | Form Catalog & Version-Aware Permanent Cache | COMPLETE | 2026-05-19 | court-forms bucket; court_forms table seeded from CSV; GET /api/forms/{num} endpoint; POST /api/forms/check-updates; harvest script. Manual gaps: browser harvest of all PDFs; OSCA contact; pg_cron app.backend_url setting |
| 3 | Statutes, Court Rules & Local AOs Corpus | COMPLETE | 2026-06-29 | statutes / court_rules / local_administrative_orders / court_closures tables; law_sources.json; /api/law/* router; ingest_statutes.py (REWRITTEN 2026-06: XML→HTML parser for current FL Legislature site). 882 sections across 24 chapters ingested (Ch. 34, 38, 47, 48, 51, 55, 56, 57, 61, 63, 68, 69, 76, 77, 79, 82, 83, 85, 86, 90, 92, 95, 110, 768). **Court rules ingest COMPLETE 2026-06-29**: 323 rules from 5 rule sets via official FL Bar PDFs (GP 56, Civil 94, Probate 121, Appellate 51, Family 1). Key rule 2.514 (time computation) verified. Small Claims needs OCR retry. Manual gap: 19th Circuit AOs (use circuit19.org) |
| 4 | The Deadline Engine | COMPLETE | 2026-05-19 | backend/deadline/rules.py (8 rules, 2.514, FL holidays); compute.py (deterministic, full trace); extract.py (LLM stage 1); pipeline.py; 16 tests pass |
| 5 | The Document Triage Classifier | COMPLETE | 2026-05-19 | backend/triage/classify.py (13 types); router.py (ALWAYS_ESCALATE_TYPES); /api/triage/* router; 16 tests pass |
| 6 | The Reminder & Notification Scheduler | COMPLETE | 2026-05-19 | reminders.py (severity-scaled schedule); notifications.py (Expo push + email stub); hourly cron endpoint; EN/ES copy; 14 tests pass. Manual gap: set app.backend_url + app.api_key in Supabase |
| 7 | The Evaluation Harness | COMPLETE | 2026-05-19 | 50-doc eval set; locked ground_truth.json; run_all.py (fast mode CI / --full manual); eval-deadline.yml CI; 45/45 pass, 34/34 fatal = 100% |
| 8 | UPL Wall & Escalation Enforcement | COMPLETE | 2026-05-19 | upl.py (5 triggers, FATAL_CONFIDENCE_THRESHOLD=0.90, URGENT_HOURS=72); EN/ES disclaimers 3 levels; /api/analysis/* router; REVIEW_TEMPLATE.md + OUTPUT_AUDIT.md; 25 tests pass. Manual gap: FL attorney review |
| 9 | Police Report Scanner: CaseContext Activation | COMPLETE | 2026-05-19 | case_context.py (empty_case_context mirrors types.ts); scanner.py extended (CASE_CONTEXT_PROMPT + extract_case_context, findings flow unchanged); police_report.py router returns case_context alongside findings; CaseContextBanner.tsx above findings; AnalyzeResponse extended; V2_LEDGER.md created |
| 10 | Form Library Ingest (167-form corpus) | COMPLETE | 2026-06-29 | migration `20260615120000_phase_10_form_library.sql`. 443 forms in court-forms bucket + court_forms: **443 published** (clean statewide-numbered, real titles, servable, AI suggestion live). forms.py serves status in (published, active). Test suite: `backend/tests/test_phase_2.py` (13 test functions). Reconcile utility: `scripts/reconcile_phase2.py`. STATUS.md added as comprehensive tracker. Forms change detection fixed: checks both "published" and "active" statuses, uses SHA-256 hash comparison. |

---

## Post-v2 Development (Post-June 2026)

Development continued beyond v2 phases, enhancing the platform with new capabilities:

### Chat Expert System
- `backend/src/agents/chat_expert.py` — Multi-module conversational interface
- `backend/src/api/routers/chat.py` — Chat endpoints
- 6 legal topics: criminal_procedure, discovery_motion, property_casualty, small_claims, wills_trusts, police_report_v2
- Frontend integration for conversational legal information

### Modern UI Redesign
- Glossy UI system with improved HomeHub tiles
- Enhanced footer component
- Improved visual styling across components

### Enhanced Modules
- **CaseContext System** — Structured case context extraction for police reports (`case_context.py`)
- **Wills & Trusts Module** — Complete new legal explainer (`backend/src/agents/wills_trusts.py`, router, frontend page)
- **PII Redaction** — Full implementation with 21 passing tests (`backend/src/ingestion/pii_redactor.py`)
- **Risk Scoring** — Applied across Discovery Motion, Property & Casualty, Police Report modules

### Opinion Retrieval (case-law corpus → product)
- **Corpus:** 759 FL appellate opinions in Supabase `legal_opinions` (ingested offline via `scripts/opinion_pipeline/`, commit `9110b20`, 2026-07). 178 distinct `situation_tags`; heavily criminal-leaning (`felony`=346, `criminal_sentencing`=263, `constitutional_challenge`=243).
- **Retrieval service:** `backend/src/services/opinion_retrieval.py` — `get_relevant_opinions(tags)` queries via `DatabaseManager` (degraded-mode-safe, fail-soft → `[]`), PostgREST `.overlaps("situation_tags", ...)`, `.eq("quality_flagged", False)`, ordered by `cite_count` desc. 13 unit + 2 live-integration tests.
- **Deterministic mapper:** `derive_situation_tags(v2_result)` — precision-over-recall. Curated booleans (`miranda_noted` / `probable_cause_present`) OWN the Miranda/probable-cause signals; free-text keyword scan reserved only for signals with no boolean (excessive force → `police_misconduct`). Emits only verified-vocabulary tags; no baseline; `[]` on no match.
- **First module wired — Police Report Analyzer** (streaming `/api/police-report/analyze`, commit `33cb1c1`, 2026-07-03): `relevant_opinions` SSE event emitted post-stream in `PoliceReportAnalyzerV2` after `risk_analysis`, sealed in its own try/except so a mapper/retrieval failure can never break an already-sent analysis. `OpinionCard.tsx` renders plain-English summary + per-case `attorney_prompt` + `cite_count` authority signal; `RelevantOpinion` type lives in `components/policereport/types.ts`.
- **Deferred:** legacy `/analyze/batch` NOT wired (frontend never calls it — dead path). Other modules (Small Claims, Eviction, Traffic, etc.) not yet wired — pattern proven on Police Report first.

### Infrastructure Improvements
- `backend/deadline/compute.py` — Simplified non-computable deadline handling (cleaner escalation)
- `backend/evals/run_all.py` — Fixed escalation detection logic, added .env support
- `scripts/ingest_statutes.py` — Complete rewrite from XML to HTML-based parsing

---

## Open manual gaps (non-engineering, gate public launch)

1. **Railway SUPABASE_SERVICE_KEY** — wrong value in `zesty-delight`; service-role JWT required (not anon key). Verify payload `"role": "service_role"` at jwt.io before pasting.
2. **Supabase anonymous sign-in** — enable in Auth dashboard (Phase 1).
3. **Presidio PII redaction** — DONE 2026-06-23. `PIIRedactor` class in `backend/src/ingestion/pii_redactor.py`; regex-based SSN/DOB/financial account/DL detection; wired into `/api/process` after extraction; 21 tests pass.
4. **Form harvest** — DONE (Phase 10): 443 forms published, AI suggestion live. `backend/tests/test_phase_2.py` covers 13 endpoints. `scripts/reconcile_phase2.py` links bucket files.
5. **OSCA contact** — initiate access arrangement (Phase 2).
6. **Supabase pg_cron app settings** — set `app.backend_url` + `app.api_key` in DB Configuration (Phases 2, 6).
7. **Statute ingest** — DONE 2026-06-29: 882 sections across 24 chapters ingested via rewritten HTML parser.
8. **19th Circuit AOs** — review `circuit19.org/administrative-orders`, seed `local_administrative_orders` (Phase 3).
9. **Full LLM eval** — DONE 2026-06-29: 33/33 fatal deadlines correct (launch gate passed). 39/44 total deadline accuracy.
10. **FL attorney review** — complete `attorney_review/REVIEW_TEMPLATE.md` with FL attorney; retain signed copy (Phase 8).
11. **Terms of Service** — draft + review (parallel workstream, gates launch).
12. **Tech E&O insurance** — obtain before public launch.
13. **Operating entity** — LLC/corp formation.
14. **Form enrichment** — DONE 2026-06-15. DeepSeek enrichment + writeback complete. 443 published forms with AI suggestion. DeepSeek enrichment (cheap agent, off-box) → `forms/enrichment_output.json` (109 records); `scripts/writeback_form_enrichment.py --execute` updated 106 rows (plain_language_summary + situation_tags + corrected titles). `situation_tags` normalized to snake_case in DB. `12.980(g)` re-enriched as a single record (Claude, DeepSeek key not on this box). Model QA flagged 2 `published` forms as not-single-form → demoted to `review` (`12.931(a)`, `12.980(j)`). State (2026-06-15): **58 published** (all enriched), 96 review. Promoted 35 Group-A `suspect_metadata` forms (clean statewide numbers + corrected titles) after title eyeball; 4 bad titles fixed first (`12.980(n)` + 3 circuit5 packets). **Follow-ups:** (a) still on `review` by design — 9 `12.980` DV/injunction forms (HOLD for attorney review), Group B eviction/probate (synthetic keys — assign real form numbers?), Group C circuit_local, Group D `12.980(o)` scanned (empty text); (b) 3 enrichment records had no catalog row (`12.930(a)`, `12.980(k)`×2) — skipped; (c) 32 `unverified` seed stubs + 1 legacy `active` row still unreconciled; (d) **`12.980` series file→number scramble** — `12.980_g_.txt` header reads `12.980(k)`, `12.980(j)`'s text was `(g)`'s; likely legacy FL renumbering, verify file→number mapping against official FL forms before trusting the numbers.
