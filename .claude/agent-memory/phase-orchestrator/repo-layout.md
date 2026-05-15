---
name: repo-layout
description: Cheatsheet mapping each Phase 0-14 deliverable to its actual file location in the repo
metadata:
  type: reference
---

Quick lookup for "where does Phase N live?" Verified 2026-05-14.

| Phase | Deliverable                         | Location |
|-------|-------------------------------------|----------|
| 0     | Project tree + requirements         | `backend/`, `frontend/`, `mobile/`, `backend/requirements.txt` |
| 0     | Jurisdictions / forms data          | `backend/src/data/jurisdictions.json`, `backend/src/data/forms_library.json` |
| 1     | PDF parser                          | `backend/src/ingestion/pdf_parser.py` |
| 1     | OCR                                 | `backend/src/ingestion/ocr.py` |
| 1     | Text cleaner                        | `backend/src/ingestion/text_cleaner.py` |
| 1     | Ingest entrypoint                   | `backend/src/ingestion/__init__.py` (`ingest_document`) |
| 2     | Config / disclaimer / escalation / i18n | `backend/src/core/{config,disclaimer,escalation,i18n}.py` |
| 2     | Notifications                       | `backend/src/platforms/notifications.py` |
| 3     | Classifier agent                    | `backend/src/agents/classifier.py` |
| 4     | Explainer agent                     | `backend/src/agents/explainer.py` |
| 5     | Form guide agent                    | `backend/src/agents/form_guide.py` |
| 6     | Risk scanner agent                  | `backend/src/agents/risk_scanner.py` |
| 7     | Expungement agent                   | `backend/src/agents/expungement.py` |
| 8     | Supabase DB manager                 | `backend/src/memory/db.py` |
| 8     | SQL schema                          | `deploy/supabase_schema.sql` |
| 9     | Stripe client                       | `backend/src/payments/stripe_client.py` |
| 10    | FastAPI app + routes                | `backend/src/api/routes.py`, `backend/main.py` |
| 11    | Florida courts (Mode A)             | `backend/src/platforms/florida_courts.py` (PDFAGenerator, CountyRouter, ManualFilingHelper) |
| 12    | Web frontend                        | `frontend/` (Vite + React + Tailwind), pages in `frontend/src/pages/` |
| 13    | Mobile app                          | `mobile/` — **empty, out of v1 scope** (see [[phase-13-mobile-out-of-scope]]) |
| 14    | Deploy config                       | `{,backend/,frontend/}{nixpacks.toml,railway.json}` (Railway) |

Test files live at `backend/test_phase{1,2,3,4,5,6,7,8,9,11}.py`. There is no
`test_phase0.py`, `test_phase10.py`, `test_phase12.py`, `test_phase13.py`, or
`test_phase14.py` — those phases verify via inline checks, route enumeration,
or are out of scope.

Also at repo root: `crash_test.py` (ad-hoc) and `test_lease.pdf` / `test_lease.txt`
(fixtures for `test_phase1.py`).
