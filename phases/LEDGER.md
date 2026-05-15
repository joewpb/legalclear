# LegalClear — Phase Ledger

**Single source of truth for build state.** The `phase-orchestrator` agent reads
this first every session and writes to it after every phase transition. If this
ledger disagrees with the actual repo, the repo wins — re-verify and correct.

Status values: `DEPLOYED` · `COMPLETE` · `PENDING` · `BLOCKED` · `STUB`
(`STUB` = phase name/spec not yet reconstructed; orchestrator must resolve before executing.)

---

## Part A — phases 0-14 · VERIFY ONLY · do not rebuild

| # | Name | Status | Last verified | Note |
|---|------|--------|---------------|------|
| 0 | Project scaffold (FastAPI / React / RN / Supabase / Stripe) | DEPLOYED | — | verify only |
| 1 | Document ingestion (PyMuPDF parser, Tesseract OCR, Supabase file storage) | DEPLOYED | — | `/api/upload` exists — do not touch |
| 2 | Classifier agent (document type, jurisdiction, metadata) | DEPLOYED | — | verify only |
| 3 | Explainer agent (plain-language summary + Q&A, disclaimer in system prompt) | DEPLOYED | — | verify only |
| 4 | Form guide agent (field-by-field walkthrough, jurisdiction-aware) | DEPLOYED | — | verify only |
| 5 | Risk scanner agent (clause scoring red/yellow/green, red-flag detection) | DEPLOYED | — | verify only |
| 6 | Output layer (structured report generation, PDF export) | DEPLOYED | — | verify only |
| 7 | Payments (Stripe pay-per-use, token gate, usage tracking in Supabase) | DEPLOYED | — | verify only |
| 8 | Web frontend (upload flow, results dashboard, Q&A, payment wall) | DEPLOYED | — | verify only |
| 9 | Mobile (React Native camera scan, OCR, shared backend logic) | DEPLOYED | — | verify only |
| 10 | **(reconstruct from repo)** | STUB | — | name/scope unknown — orchestrator: inspect repo, propose spec |
| 11 | **(reconstruct from repo)** | STUB | — | name/scope unknown — orchestrator: inspect repo, propose spec |
| 12 | **(reconstruct from repo)** | STUB | — | name/scope unknown — orchestrator: inspect repo, propose spec |
| 13 | **(reconstruct from repo)** | STUB | — | name/scope unknown — orchestrator: inspect repo, propose spec |
| 14 | **(reconstruct from repo)** | STUB | — | name/scope unknown — orchestrator: inspect repo, propose spec |

## Part B — phases 15-23 · BUILD TARGET

Mapping below is **reconstructed from the v1 deployment smoke test** — confirm
each phase name and scope against the source build prompt before executing.

| # | Name (reconstructed — confirm) | Status | Note |
|---|------|--------|------|
| 15 | Hub + Small Claims tile (entry UI) | PENDING | confirm scope vs source |
| 16 | Small Claims 5-step wizard | PENDING | confirm scope vs source |
| 17 | i18n layer (en/es) + review screen with language toggle | PENDING | confirm scope vs source |
| 18 | Filing Packet generation (3 PDFs bundled to ZIP) | PENDING | confirm scope vs source |
| 19 | Stripe "LegalClear Filing Packet" $35 product + pay flow + `?paid=1` gated download | PENDING | confirm scope vs source |
| 20 | Florida courts walkthrough (8+ steps, myflcourtaccess.com) | PENDING | confirm scope vs source |
| 21 | Tracking page (confirmation number → status updates) | PENDING | confirm scope vs source |
| 22 | Integration wire-up + polish | PENDING | confirm scope vs source |
| 23 | Full v1 verification + Railway deploy | PENDING | emits final report |

---

## Open gaps — orchestrator must resolve

1. **Phases 10-14** — names and specs not in hand. Orchestrator: inspect the
   deployed repo, reconstruct each phase's actual scope, propose for confirmation.
2. **Phases 15-23** — mapping is reconstructed from the smoke test, not the
   verbatim source. Confirm against the original build prompt (compiled in the
   "Open claw architecture overview" chat) before executing each phase.
3. Until a STUB row is resolved, the orchestrator does not execute past it.
