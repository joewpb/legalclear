---
name: repo-layout
description: Map of each Phase 0-14 deliverable to its actual repo path, plus where source-vs-repo paths diverge
metadata:
  type: reference
---

Quick lookup for "where does Phase N live?" — verified against
`phases/source/` on 2026-05-14.

`source path` = where the source spec expects the artifact.
`repo path` = where the artifact actually is in the repo.
"—" = same as source path.

| Phase | Artifact                          | Source path                        | Repo path |
|-------|-----------------------------------|------------------------------------|-----------|
| 0     | uv project file                   | `backend/pyproject.toml`           | **MISSING** — repo has only `backend/requirements.txt` |
| 0     | Directory tree                    | `backend/src/{agents,api,memory,services,platforms,data}/` | `backend/src/{agents,api,core,data,ingestion,memory,payments,platforms}/` (extra `core`, `payments`, `ingestion`; **missing `services/`**) |
| 0     | Env file                          | `backend/.env`                     | — |
| 1     | DB / DatabaseManager              | `backend/src/memory/db.py`         | — |
| 2     | PDF processor                     | `backend/src/services/pdf_processor.py` | `backend/src/ingestion/pdf_parser.py` (+ `ocr.py`, `text_cleaner.py`) — different module name + dir |
| 3     | Classifier agent                  | `backend/src/agents/classifier.py` | — |
| 4     | Explainer agent                   | `backend/src/agents/explainer.py`  | — |
| 5     | Form guide agent                  | `backend/src/agents/form_guide.py` | — |
| 6     | Risk scanner agent                | `backend/src/agents/risk_scanner.py` | — |
| 7     | Expungement agent                 | `backend/src/agents/expungement.py` | — |
| 8     | Supabase wiring in db.py          | `backend/src/memory/db.py` (Supabase code path) | — |
| 8     | SQL schema                        | (not specified)                    | `deploy/supabase_schema.sql` |
| 9     | Stripe payments                   | `backend/src/services/payments.py` | `backend/src/payments/stripe_client.py` — different dir + module name |
| 10    | FastAPI app entrypoint            | `backend/src/api/main.py`          | `backend/main.py` (entrypoint) + `backend/src/api/routes.py` (consolidated routes) — split, not unified |
| 10    | Endpoint paths                    | `/api/*` (`/api/upload`, `/api/chat`, `/api/eligibility`, `/api/stripe/webhook`, `/api/push/register`, `/health`) | bare paths (`/upload`, `/chat/{document_id}`, `/eligibility`, `/webhook`, `/user/{user_id}/push-token`, `/health`) — different prefix scheme + some different names |
| 11    | Florida courts (Mode A)           | `backend/src/platforms/florida_courts.py` | — — but contains 5 unmarked `myflcourtaccess` strings; Phase 23 `test_no_mode_b` will fail unless Phase 23 deprecates the file or adds `# walkthrough text only` markers |
| 12    | Web frontend                      | `frontend/` (`.tsx`, App.tsx, Tailwind, Vite) | — but 100% `.jsx` (0 `.tsx`); Vite TS config missing |
| 12    | Existing pages                    | (not enumerated in source)         | `frontend/src/pages/{LandingPage,UploadFlow,AnalysisDashboard,ResultsPage,PaywallPage,ExpungementPage}.jsx` — `ExpungementPage.jsx` is multi-state, NOT a Phase 17 artifact |
| 13    | Mobile app                        | `mobile/{App.tsx,app.json,package.json}` | `mobile/` is empty (NOT BUILT, no-block per source) |
| 14    | Deploy config                     | Railway (`nixpacks.toml`, `railway.json`) + optional systemd/nginx | Railway only — `{,backend/,frontend/}{nixpacks.toml,railway.json}` |

## Backend ad-hoc / non-source modules

`backend/src/core/{config,disclaimer,escalation,i18n}.py` and
`backend/src/platforms/notifications.py` exist in the repo but are NOT
named as Part A deliverables in any source file. They're internal
support modules. Leave them alone; don't flag absence; don't claim
them as a phase deliverable.

## Backend tests

Repo has `backend/test_phase{1,2,3,4,5,6,7,8,9,11}.py` at backend/ root
(legacy test files from earlier phased build attempts). Source Part B
expects `backend/tests/test_phase_{15..23}.py` and
`backend/tests/test_full_v1.py` under a `tests/` subdir — that directory
does not exist yet. Part B phases will create it.

## Part B repo state (as of 2026-05-14)

**0% built.** None of the Part B frontend pages exist
(`HomeHub.tsx`, `SmallClaimsFL.tsx`, `ExpungementFL.tsx`,
`LandlordTenantFL.tsx`, `FormsFinderFL.tsx`, `TrafficFL.tsx`,
`PoliceReportAnalyzer.tsx`, `CaseLawLookupFL.tsx`, `FilingPacket.tsx`).
None of the Part B backend modules exist (`backend/src/api/routes/` is
missing; no `small_claims.py`, `landlord.py`, `traffic.py`,
`police_report.py`, `case_law.py`, `packet.py`; no
`backend/src/services/{packet_builder,pdfa_generator,county_router,
translation_layer}.py`; no `backend/src/agents/scanner.py`; no
`backend/src/templates/`; no `backend/storage/packets/`).

Related: [[part-a-source-divergences]], [[source-canonical]].
