---
name: source-canonical
description: Per-phase verbatim source spec lives at phases/source/PHASE_NN_*.md — 25 files (README + phase_00..23); supersedes LegalClear_OneShot_Prompt.md
metadata:
  type: reference
---

**Canonical source for every phase:** `phases/source/PHASE_NN_*.md`.

Layout:
```
phases/source/
├── README.md                            # universal rules + phase index + workflow
├── PHASE_00_setup.md                    # scaffold + venv (VERIFY)
├── PHASE_01_memory.md                   # DB / memory layer (VERIFY)
├── PHASE_02_pdf_processor.md            # PDF + OCR pipeline (VERIFY)
├── PHASE_03_classifier_agent.md         # (VERIFY)
├── PHASE_04_explainer_agent.md          # (VERIFY)
├── PHASE_05_form_guide_agent.md         # (VERIFY)
├── PHASE_06_risk_scanner_agent.md       # (VERIFY)
├── PHASE_07_expungement_agent.md        # (VERIFY)
├── PHASE_08_supabase.md                 # Supabase production migration (VERIFY)
├── PHASE_09_payments.md                 # Stripe ($5/$10/$15 + $20/mo + 1 free) (VERIFY)
├── PHASE_10_api.md                      # FastAPI consolidation, /api/* prefix (VERIFY)
├── PHASE_11_fl_courts_v1.md             # FL Courts Mode A scaffold (VERIFY)
├── PHASE_12_web_frontend.md             # React + Vite + Tailwind, .tsx (VERIFY)
├── PHASE_13_mobile_app.md               # Expo / RN (VERIFY, no-block)
├── PHASE_14_deploy.md                   # Railway / nginx (VERIFY)
├── PHASE_15_hub_restructure.md          # 8-tile HomeHub + Brutalist CSS (BUILD)
├── PHASE_16_small_claims.md             # 5-step wizard + 67 counties (BUILD)
├── PHASE_17_expungement_ui.md           # FL-only quiz UI wrapping Phase 07 (BUILD)
├── PHASE_18_landlord_tenant.md          # 3 sub-flows: deposit/repairs/eviction (BUILD)
├── PHASE_19_forms_finder.md             # static data-driven, ≥18 entries (BUILD)
├── PHASE_20_traffic.md                  # 3 paths: pay/school/contest (BUILD)
├── PHASE_21_police_report.md            # new Scanner agent + multi-file upload (BUILD)
├── PHASE_22_case_law.md                 # CourtListener RAG-only (BUILD)
└── PHASE_23_packet_builder.md           # PacketBuilder + PDF/A + EN/ES + $35 Stripe (BUILD, final)
```

Earlier files at repo root (`LegalClear_OneShot_Prompt.md`,
`Complete One Shot Build.md`) are superseded for spec purposes — they
cover only phases 0-14, with names that drift from `phases/source/` in
several places (e.g., the oneshot's "core utilities" / "ingestion"
ordering doesn't match source's "memory" / "pdf_processor" ordering).
Keep the oneshot for historical context; do not use it to drive
verification.

**`phases/PHASE_SPECS.md`** is the orchestrator's thin index OVER the
source files. **`phases/LEDGER.md`** tracks per-phase status. Both refer
back to `phases/source/` for full spec content.

**Reference snapshots** (informational only, not authoritative) of
pre-existing Part A frontend pages live at `phases/reference/`.

**How to apply:** when the orchestrator needs goal / verify command /
deliverables / pass criteria for any phase, read the corresponding
`phases/source/PHASE_NN_*.md` directly. Do not rely on summaries in
PHASE_SPECS.md or LEDGER.md for execution detail — those are indexes
only.
