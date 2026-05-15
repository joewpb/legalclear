---
name: phase-numbering-correction
description: Canonical Part A phase names per phases/source/ — two prior mappings were wrong; this is the authoritative one
metadata:
  type: project
---

**Canonical Part A mapping (from `phases/source/PHASE_NN_*.md`, 2026-05-14):**

| # | Title                                          | Source file |
|---|------------------------------------------------|-------------|
| 0 | Project Setup (scaffold + venv)                 | `PHASE_00_setup.md` |
| 1 | Memory Layer (DB) — `db.py`, `DatabaseManager`  | `PHASE_01_memory.md` |
| 2 | PDF Processing Pipeline — `pdf_processor.py`    | `PHASE_02_pdf_processor.md` |
| 3 | Classifier Agent                                | `PHASE_03_classifier_agent.md` |
| 4 | Explainer Agent                                 | `PHASE_04_explainer_agent.md` |
| 5 | Form Guide Agent                                | `PHASE_05_form_guide_agent.md` |
| 6 | Risk Scanner Agent                              | `PHASE_06_risk_scanner_agent.md` |
| 7 | Expungement Agent                               | `PHASE_07_expungement_agent.md` |
| 8 | Supabase Production DB migration                | `PHASE_08_supabase.md` |
| 9 | Stripe Payments                                 | `PHASE_09_payments.md` |
| 10 | FastAPI Backend Consolidation                  | `PHASE_10_api.md` |
| 11 | FL Courts Mode A v1                            | `PHASE_11_fl_courts_v1.md` |
| 12 | Web Frontend v1                                | `PHASE_12_web_frontend.md` |
| 13 | Mobile App (Expo / RN)                         | `PHASE_13_mobile_app.md` |
| 14 | Deploy (Railway / nginx)                       | `PHASE_14_deploy.md` |

## Prior wrong mappings (do NOT trust artifacts that use these)

**Wrong mapping #1 — pre-2026-05-14 ledger:** had Phase 1 = "Document
ingestion", Phase 2 = "Classifier", Phases 10-14 as STUB. Numbers shifted
by 1 from Phase 2 onward.

**Wrong mapping #2 — 2026-05-14 v2 PHASE_SPECS.md and ledger
(self-correcting attempt against the oneshot):** had Phase 1 = "Document
ingestion", Phase 2 = "Core utilities (config/disclaimer/escalation/i18n)",
Phase 8 = "Memory layer (Supabase DatabaseManager)". This swapped the
memory layer (real Phase 1) with the Supabase migration (real Phase 8)
and invented a "Core utilities" phase that doesn't exist as a labeled
phase in the source. Part B subjects 17-22 were also entirely wrong.

**Why this matters:** prior reconciliation reports, commit messages, and
ledger entries may still reference these wrong names. If you see "Phase 8
Memory layer" or "Phase 17 i18n" or "Phase 22 Integration polish" in any
artifact, that artifact is using a wrong mapping. Re-map against the
table above before trusting any claim.

**How to apply:** when reading any older artifact that references Part A
or Part B phase numbers/titles, sanity-check against the canonical table
above. Trust `phases/source/` over any summary.
