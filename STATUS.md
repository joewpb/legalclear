# LegalClear — Build Status

**Generated:** 2026-06-23 · **Source of truth:** repo files + `phases/LEDGER.md` + `phases/V2_LEDGER.md`

---

## v1 — 24 Phases (phases/source/PHASE_00–23)

### Part A — Phases 00–14 · ✅ VERIFY ONLY (do not rebuild)

| # | Phase | Status |
|---|-------|--------|
| 00 | Project scaffold + venv | ✅ DEPLOYED |
| 01 | DB / memory layer (SQLite → Supabase) | ✅ DEPLOYED |
| 02 | PDF extraction + OCR pipeline | ✅ DEPLOYED |
| 03 | Classifier Agent | ✅ DEPLOYED |
| 04 | Explainer Agent | ✅ DEPLOYED |
| 05 | Form Guide Agent | ✅ DEPLOYED |
| 06 | Risk Scanner Agent | ✅ DEPLOYED |
| 07 | Expungement Agent | ✅ DEPLOYED |
| 08 | Supabase production DB | ✅ DEPLOYED |
| 09 | Stripe paywall | ✅ DEPLOYED |
| 10 | FastAPI backend consolidation | ✅ DEPLOYED |
| 11 | FL Courts Mode A initial | ✅ DEPLOYED |
| 12 | React + Tailwind frontend | ✅ DEPLOYED |
| 13 | React Native (Expo) | ✅ DEPLOYED |
| 14 | Railway / nginx deploy | ✅ DEPLOYED |

### Part B — Phases 15–23 · ✅ ALL BUILT & DEPLOYED

| # | Phase | Status |
|---|-------|--------|
| 15 | 8-tile HomeHub + Brutalist CSS | ✅ DEPLOYED |
| 16 | Small Claims FL wizard | ✅ DEPLOYED |
| 17 | Expungement quiz UI + endpoint | ✅ DEPLOYED |
| 18 | Landlord/Tenant 3 sub-flows | ✅ DEPLOYED |
| 19 | Court Forms Finder (data-driven) | ✅ DEPLOYED |
| 20 | Traffic/Tickets wizard | ✅ DEPLOYED |
| 21 | Police Report Analyzer | ✅ DEPLOYED |
| 22 | FL Case Law Lookup (CourtListener) | ✅ DEPLOYED |
| 23 | Mode A Filing Pipeline (PDF/A + EN/ES + $35 Stripe) | ✅ DEPLOYED |

**v1 shipped 2026-05-15.** Rethemed (light mode) same day. Live on Railway.

---

## v2 — 11 Phases (phases/BUILD_PLAN.md + extensions)

| # | Phase | Status | Date |
|---|-------|--------|------|
| 0 | Stabilize the Foundation | ✅ COMPLETE | 2026-06-23 |
| 1 | Database Schema, Security & PII | ✅ COMPLETE | 2026-06-23 |
| 2 | Form Catalog & Version-Aware Permanent Cache | ✅ COMPLETE | 2026-05-19 |
| 3 | Statutes, Court Rules & Local AOs Corpus | ✅ COMPLETE | 2026-05-19 |
| 4 | The Deadline Engine | ✅ COMPLETE | 2026-05-19 |
| 5 | The Document Triage Classifier | ✅ COMPLETE | 2026-05-19 |
| 6 | The Reminder & Notification Scheduler | ✅ COMPLETE | 2026-05-19 |
| 7 | The Evaluation Harness | ✅ COMPLETE | 2026-05-19 |
| 8 | UPL Wall & Escalation Enforcement | ✅ COMPLETE | 2026-05-19 |
| 9 | Police Report Scanner: CaseContext Activation | ✅ COMPLETE | 2026-05-19 |
| 10 | Form Library Ingest (167-form corpus) | ✅ COMPLETE | 2026-06-15 |

**All v2 phases complete.** 154 forms in court-forms bucket (58 published, 96 in review).

---

## What's Actually in the Repo (beyond v1/v2 specs)

### Frontend pages (15 `.tsx` files in `frontend/src/pages/`)
- **v1 Part B:** `HomeHub`, `SmallClaimsFL`, `ExpungementFL`, `LandlordTenantFL`, `FormsFinderFL`, `TrafficFL`, `PoliceReportAnalyzer`, `CaseLawLookupFL`, `FilingPacket`
- **Beyond spec:** `CriminalProcedureExplainer`, `DiscoveryMotionAnalyzer`, `PropertyCasualtyExplainer`, `SmallClaimsExplainer`, `WillsTrustsExplainer`, `PhaseStub`

### Backend agents (14 in `backend/src/agents/`)
- **v1:** `classifier`, `explainer`, `form_guide`, `risk_scanner`, `expungement`, `scanner`
- **Beyond spec:** `case_context`, `chat_expert`, `criminal_procedure`, `discovery_motion`, `police_report_v2`, `property_casualty`, `small_claims`, `wills_trusts`

### Backend routers (20 in `backend/src/api/routers/`)
- **v1 Part B:** `small_claims`, `expungement`, `landlord`, `traffic`, `police_report`, `case_law`, `packet`
- **v2:** `forms`, `law`, `triage`, `deadline`, `reminders`, `analysis`, `intake`
- **Beyond spec:** `criminal`, `discovery`, `property_casualty`, `wills_trusts`, `chat`

### v2 backend modules
- **Deadline engine:** `backend/deadline/` — `rules.py`, `compute.py`, `extract.py`, `pipeline.py`
- **Triage:** `backend/triage/` — `classify.py` (13 doc types), `router.py`
- **UPL wall:** `backend/src/core/upl.py` — 5 triggers, guardrails, disclaimers
- **Reminders:** `backend/src/core/reminders.py` — severity-scaled schedule
- **Notifications:** `backend/src/core/notifications.py` — Expo push + email stub
- **Ingestion:** `backend/src/ingestion/` — `pdf_parser.py`, `ocr.py`, `pii_redactor.py`, `text_cleaner.py`
- **Evals:** `backend/evals/run_all.py` — 50-doc eval set, 100% pass rate

### v2 services
- `county_router.py` — routes to correct FL county clerk
- `translation_layer.py` — EN/ES translation support

### Data files (`backend/src/data/`)
- `fl_county_clerk_details.json`, `fl_disqualifying_offenses.json`, `forms_library.json`, `law_sources.json`, `jurisdictions.json`, `instructions_en.json`, `instructions_es.json`, `walkthrough_steps_en.json`, `walkthrough_steps_es.json`

### Database
- **Migrations:** `backend/migrations/2026_05_15_packets.sql`
- **v2 tables:** `trigger_events`, `deadlines`, `deadline_reminders`, `court_forms`, `billing_events`, `statutes`, `court_rules`, `local_administrative_orders`, `court_closures`
- **RLS:** 9 policies active across all tables
- **pg_cron:** retention jobs active (30-day doc purge, 72-hour guest purge)

---

## OPEN ITEMS — What Still Needs Work

### 🔴 Blocking / High Priority

| # | Item | Category | Notes |
|---|------|----------|-------|
| 1 | **Railway `SUPABASE_SERVICE_KEY`** | Infrastructure | Wrong value in `zesty-delight`. Needs service-role JWT (verify `"role": "service_role"` at jwt.io). Currently may be anon key. |
| 2 | **Supabase anonymous sign-in** | Infrastructure | Must be enabled in Supabase Auth dashboard. Blocked by Cloudflare — PAT exists but `api.supabase.com` unreachable from this host. |
| 3 | **Supabase pg_cron `app.backend_url` + `app.api_key`** | Infrastructure | Set in DB Configuration so cron jobs can call the backend (Phases 2, 6). |
| 4 | **Run statute ingest** | Data | ✅ DONE 2026-06-29 — 882 sections across 24 chapters ingested (Ch. 34, 38, 47, 48, 51, 55, 56, 57, 61, 63, 68, 69, 76, 77, 79, 82, 83, 85, 86, 90, 92, 95, 110, 768). Chapter 84 had no parseable sections (bad URL). |
| 5 | **19th Circuit AOs** | Data | Review `19thcircuit.org/administrative-orders`, seed `local_administrative_orders` table (Phase 3). |

### 🟡 Medium Priority

| # | Item | Category | Notes |
|---|------|----------|-------|
| 6 | **Full LLM eval** | Quality | ✅ RUN 2026-06-29 — **LAUNCH GATE PASSED**: 33/33 fatal deadlines correct. 39/44 total deadline accuracy. 5 high-severity mismatches on SC-001–005 (non-blocking). 46/50 doc-type, 44/45 trigger-date, 38/45 service-method. |
| 7 | **OSCA contact** | Legal/Ops | Initiate access arrangement with Office of the State Courts Administrator for form acquisition (Phase 2). |
| 8 | **Form file→number scramble** | Data | `12.980` series has known file↔number mismatches. 10 `failed_extraction` forms need OCR re-run. 49 `harvest_import` county-local forms need text extraction. |
| 9 | **32 unverified seed stubs** | Data | ✅ DELETED 2026-06-29. No content, no files — ghost entries from seed CSV. |
| 10 | **90 forms in review** | Data | 49 harvest_import (no text extraction), 10 failed_extraction (needs OCR), 31 admin/info kept in review. Non-blocking.

### 🟢 Lower Priority / Parallel Workstreams (Joe + attorneys)

| # | Item | Category | Notes |
|---|------|----------|-------|
| 11 | **FL attorney review** | Legal | Complete `attorney_review/REVIEW_TEMPLATE.md` with FL attorney; retain signed copy (Phase 8). |
| 12 | **Terms of Service** | Legal | Draft + attorney review. Gates public launch. |
| 13 | **Tech E&O insurance** | Legal/Ops | Obtain before public launch. |
| 14 | **Operating entity** | Legal/Ops | LLC/corp formation. |
| 15 | **Group B eviction/probate forms** | Data | Synthetic keys — need real form numbers assigned. |
| 16 | **Group C circuit_local forms** | Data | Need review/filtering. |
| 17 | **`12.980(o)` scanned form** | Data | Empty text extraction — needs OCR or manual entry. |

---

## Deploy Targets

| Surface | Railway Service | Status |
|---------|----------------|--------|
| Backend | `zesty-delight` | ✅ Live (port 8001) |
| Frontend | `appealing-victory` | ✅ Live |

**Stripe product:** "LegalClear Filing Packet" at **$35.00** · **Languages:** `en`, `es`

---

## Quick Health Check

```bash
# Backend
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/health

# Frontend (Vite dev)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/

# All v2 tests
cd backend && uv run python -m pytest tests/ -q
```
