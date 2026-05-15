# LegalClear — Phase Ledger

**Single source of truth for build state.** The `phase-orchestrator` agent reads
this first every session and writes to it after every phase transition. If this
ledger disagrees with the actual repo, the repo wins — re-verify and correct.

Status values: `DEPLOYED` · `COMPLETE` · `PENDING` · `BLOCKED` · `OUT-OF-SCOPE`

Part A naming and scopes here are transcribed from the verbatim source build
prompt `LegalClear_OneShot_Prompt.md` (== `Complete One Shot Build.md`), then
re-verified phase-by-phase against the live repo on 2026-05-14.

---

## Part A — phases 0-14 · VERIFY ONLY · do not rebuild

| #  | Name (canonical, from oneshot) | Status | Last verified | Note |
|----|--------------------------------|--------|---------------|------|
| 0  | Scaffold (dirs + requirements.txt + uv venv + jurisdictions/forms data) | DEPLOYED | 2026-05-14 | `requirements.txt` + `uv venv` is the canonical form per oneshot — pyproject.toml is NOT required. `playwright` listed but unused in `backend/src/` — keep an eye on it, not a Mode B violation today |
| 1  | Document ingestion (PyMuPDF parser, Tesseract OCR, text_cleaner, ingest_document) | DEPLOYED | 2026-05-14 | `/api/upload` exists in `backend/src/api/routes.py:127` — do not touch |
| 2  | Core utilities (config, disclaimer, escalation router, i18n, notifications) | DEPLOYED | 2026-05-14 | `backend/src/core/{config,disclaimer,escalation,i18n}.py` + `platforms/notifications.py` |
| 3  | Classifier agent (document type, jurisdiction, metadata, price tiers) | DEPLOYED | 2026-05-14 | `backend/src/agents/classifier.py` — typed dict return |
| 4  | Explainer agent (plain-language summary + Q&A, disclaimer in system prompt) | DEPLOYED | 2026-05-14 | `backend/src/agents/explainer.py` — disclaimer via `core/disclaimer.py` |
| 5  | Form guide agent (field-by-field walkthrough, jurisdiction-aware) | DEPLOYED | 2026-05-14 | `backend/src/agents/form_guide.py` — loads `forms_library.json` |
| 6  | Risk scanner agent (RED/YELLOW/GREEN clause scoring) | DEPLOYED | 2026-05-14 | `backend/src/agents/risk_scanner.py` — three-tier counts in response |
| 7  | Expungement agent (eligibility + petition guide) | DEPLOYED | 2026-05-14 | `backend/src/agents/expungement.py` — wired into `/eligibility` route |
| 8  | Memory layer (Supabase DatabaseManager + schema SQL) | DEPLOYED | 2026-05-14 | `backend/src/memory/db.py` (`usage_stats` table); schema at `deploy/supabase_schema.sql` |
| 9  | Payments (Stripe pay-per-use + subscription + webhook) | DEPLOYED | 2026-05-14 | `backend/src/payments/stripe_client.py` + `/subscribe/{user_id}` + `/webhook` routes |
| 10 | API (FastAPI app + endpoints + singleton wiring) | DEPLOYED | 2026-05-14 | `backend/src/api/routes.py` — `/health`, `/user`, `/upload`, `/process`, `/chat`, `/document(s)`, `/eligibility`, `/florida-filing/prepare`, `/webhook`, `/subscribe` |
| 11 | Florida courts (PDFAGenerator + CountyRouter + ManualFilingHelper) | DEPLOYED | 2026-05-14 | `backend/src/platforms/florida_courts.py` — Mode A only. Oneshot's optional Mode B portal automation is **superseded** by AGENTS.md §7 (Mode B in `backend/src/` = hard fail) |
| 12 | Web frontend (React + Vite + Tailwind + Stripe.js + i18next) | DEPLOYED | 2026-05-14 | `frontend/` — Upload/Results/Paywall views. `i18next` dep installed but en/es wiring is deferred to Part B Phase 17 |
| 13 | Mobile app (Expo / React Native) | OUT-OF-SCOPE | 2026-05-14 | `mobile/` intentionally empty. Dropped from v1 scope. Do **not** build, do **not** count as a fail |
| 14 | Deploy (services live, frontend builds, smoke tests pass) | DEPLOYED | 2026-05-14 | Railway via `nixpacks.toml` + `railway.json` (services `zesty-delight`, `appealing-victory`). Oneshot's systemd + nginx plan is **superseded** by Railway, same precedent as Mode B hardening |

## Part B — phases 15-23 · BUILD TARGET · HARD STOP UNTIL SOURCE LANDS

Verbatim source for Part B lives in `LegalClear_Complete_Phases_0-23.md` (to be
supplied). All nine `<<< SOURCE >>>` markers in `PHASE_SPECS.md` are unresolved.
**Do not execute any Part B phase until that document is in the repo.**

| #  | Name (reconstructed — confirm against source on arrival) | Status | Note |
|----|----------------------------------------------------------|--------|------|
| 15 | Hub + Small Claims tile (entry UI)                        | PENDING | source missing — hard stop |
| 16 | Small Claims 5-step wizard                                | PENDING | source missing — hard stop |
| 17 | i18n layer (en/es) + review screen with language toggle   | PENDING | source missing — hard stop |
| 18 | Filing Packet generation (3 PDFs bundled to ZIP)          | PENDING | source missing — hard stop |
| 19 | Stripe "LegalClear Filing Packet" $35 + `?paid=1` gate    | PENDING | source missing — hard stop |
| 20 | Florida courts walkthrough (8+ steps, myflcourtaccess.com) | PENDING | builds on Phase 11; Mode A only |
| 21 | Tracking page (confirmation number → status updates)      | PENDING | source missing — hard stop |
| 22 | Integration wire-up + polish                              | PENDING | source missing — hard stop |
| 23 | Full v1 verification + Railway deploy + final report      | PENDING | source missing — hard stop |

---

## Open gaps — orchestrator must resolve

1. **Part B source document** (`LegalClear_Complete_Phases_0-23.md`) must be
   supplied before any Phase 15-23 execution begins. Until then, every Part B
   `<<< SOURCE >>>` marker in `PHASE_SPECS.md` is unresolved and the orchestrator
   halts at Phase 14.
2. **Phase 0 `playwright` dependency** — listed in `requirements.txt` but not
   imported in `backend/src/`. Not a Mode B violation as written, but it's a
   landmine. Recommend removing during Part B polish (Phase 22) unless
   something starts using it.
3. **Phase 12 i18n wiring** — `i18next` is in `package.json` but no
   `useTranslation` / `i18n.init` calls in `frontend/src/`. This is expected
   (Part B Phase 17 wires en/es) but record it here so it doesn't get
   re-flagged as a Phase 12 regression.
