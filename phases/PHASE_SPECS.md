# LegalClear — Phase Specs (Index)

**The verbatim source spec for every phase lives in `phases/source/PHASE_NN_*.md`.**
That directory is canonical. This file is a thin orchestrator-facing index over
it. If this file disagrees with the source files, the source files win — re-read
them and correct this index.

Supersedes the prior v2 of `PHASE_SPECS.md`. The v2 had Part A phase 1/2/8 names
wrong and Part B phase 17-23 subjects almost entirely wrong; the source files
land them correctly.

---

## Universal rules (from `phases/source/README.md`)

- **uv only.** No `pip`, no `python3` direct.
- **Backend on 8001.** Port 8000 is Nemotron's inference container — the app
  must not bind there.
- **No automation against `myflcourtaccess.com`.** Mode A only. Phase 23 has
  a hard test (`test_no_mode_b`) that scans every `.py` file under
  `backend/src/` for the literal string `myflcourtaccess`; any non-commented
  match fails the build. Walkthrough text strings are permitted only when the
  enclosing file carries a `# walkthrough text only` comment.
- **Florida jurisdiction only** in v1.
- **Brutalist design tokens** (defined in Phase 15) are mandatory on every
  new frontend component from Phase 15 onward.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output before `json.loads()`;
  retry once on parse failure.

---

## Part A — phases 0-14 — VERIFY ONLY

Each phase's full spec (goal, verify command, pass criteria, contract) lives
in the source file. The orchestrator runs the verify command, confirms what
exists, and never rebuilds. Reality-vs-source divergences are listed below
the table.

| #  | Source file                            | Title                                       | Status                  |
|----|----------------------------------------|---------------------------------------------|-------------------------|
| 0  | `phases/source/PHASE_00_setup.md`       | Project scaffold + venv                     | DEPLOYED — divergence   |
| 1  | `phases/source/PHASE_01_memory.md`      | DB / memory layer (`db.py`, `DatabaseManager`) | DEPLOYED               |
| 2  | `phases/source/PHASE_02_pdf_processor.md` | PDF extraction + OCR pipeline             | DEPLOYED — divergence   |
| 3  | `phases/source/PHASE_03_classifier_agent.md` | Classifier Agent                       | DEPLOYED                |
| 4  | `phases/source/PHASE_04_explainer_agent.md`  | Explainer Agent                        | DEPLOYED                |
| 5  | `phases/source/PHASE_05_form_guide_agent.md` | Form Guide Agent                       | DEPLOYED                |
| 6  | `phases/source/PHASE_06_risk_scanner_agent.md` | Risk Scanner Agent                   | DEPLOYED                |
| 7  | `phases/source/PHASE_07_expungement_agent.md` | Expungement Agent                     | DEPLOYED                |
| 8  | `phases/source/PHASE_08_supabase.md`     | Supabase production DB migration            | DEPLOYED                |
| 9  | `phases/source/PHASE_09_payments.md`     | Stripe paywall ($5/$10/$15 + $20/mo + 1 free) | DEPLOYED — re-verify  |
| 10 | `phases/source/PHASE_10_api.md`          | FastAPI backend consolidation               | DEPLOYED — divergence   |
| 11 | `phases/source/PHASE_11_fl_courts_v1.md` | FL Courts Mode A scaffold                   | DEPLOYED — see Phase 23 |
| 12 | `phases/source/PHASE_12_web_frontend.md` | React + Tailwind frontend                   | DEPLOYED — divergence   |
| 13 | `phases/source/PHASE_13_mobile_app.md`   | React Native (Expo)                         | NOT BUILT — no-block    |
| 14 | `phases/source/PHASE_14_deploy.md`       | Railway / nginx deploy                      | DEPLOYED                |

### Part A — repo-vs-source divergences (all resolved 2026-06-05)

1. **Phase 0 — RESOLVED.** `backend/pyproject.toml` (894 B) + `backend/uv.lock`
   (599 KB) both present, committed 2026-05-15. `uv add` commands in Phases
   22/23 ran successfully. Was the hard Part B blocker; no longer.
2. **Phase 2 — RESOLVED.** Pipeline lives at `backend/src/ingestion/`; no
   `services/pdf_processor.py`. Phase 21's `police_report.py` imports the real
   symbol `from src.ingestion import ingest_document` instead of the source's
   `from ..services.pdf_processor import extract`. No shim needed.
3. **Phase 10 — RESOLVED (was non-blocker).** Part A endpoints stay at bare
   paths; every Part B router declares its own `prefix="/api/..."`. Confirmed
   in repo — no conflict.
4. **Phase 11 — RESOLVED.** `florida_courts.py` line 5 carries the
   `# walkthrough text only` marker. The 4 other `myflcourtaccess` hits under
   `backend/src/` are all in `data/*.json` (walkthrough/instructions text),
   which `test_no_mode_b` does not scan (Python files only). Phase 23
   `test_no_mode_b` passes.
5. **Phase 12 — RESOLVED.** Frontend converted to TS: 44 `.tsx` files, 8
   `.jsx` holdovers (legacy, `allowJs: true`). All Part B pages are `.tsx`.
6. **Phase 13** — source says mobile is built (`mobile/App.tsx`,
   `mobile/app.json`). Repo `mobile/` is empty. Source policy: "Note it in
   the final report but do NOT block. Mobile is deferred." Phase 13 source
   is explicit: "**Mobile work is OUT OF SCOPE for Phases 15–23.**" So
   empty `mobile/` is a documented Part A gap, not a Part B blocker.

---

## Part B — phases 15-23 — BUILT + DEPLOYED (v1 shipped 2026-05-15)

**This section's table and notes below were stale.** They previously read
"all PENDING / Part B is 0% built." That was wrong: `phases/LEDGER.md` and the
repo both confirm all 9 Part B phases COMPLETE and deployed. The 6 Part A
divergences listed above are all resolved (see LEDGER "Open gaps", all struck).
Reconciled 2026-06-05 against repo. The notes below are retained for historical
context only and no longer describe current state.

Each phase's full spec (deliverables, code blocks, test, pass criteria) lives
in the source file. The orchestrator builds the phase per the source, runs
its `test_phase_NN.py`, and marks the row COMPLETE only when every assertion
in the source passes.

| #  | Source file                              | Title                                                            | Status                  |
|----|------------------------------------------|------------------------------------------------------------------|-------------------------|
| 15 | `phases/source/PHASE_15_hub_restructure.md` | Hub Restructure + Brutalist Design System (8-tile HomeHub)    | COMPLETE 2026-05-14     |
| 16 | `phases/source/PHASE_16_small_claims.md` | Small Claims FL 5-step wizard + 67-county data                   | COMPLETE 2026-05-15     |
| 17 | `phases/source/PHASE_17_expungement_ui.md` | Expungement FL UI: 5-question quiz + `/api/expungement/*`      | COMPLETE 2026-05-15     |
| 18 | `phases/source/PHASE_18_landlord_tenant.md` | Landlord/Tenant FL: 3 sub-flows (deposit / repairs / eviction) | COMPLETE 2026-05-15     |
| 19 | `phases/source/PHASE_19_forms_finder.md` | Court Forms Finder FL (frontend-only, data-driven, ≥18 entries)  | COMPLETE 2026-05-15     |
| 20 | `phases/source/PHASE_20_traffic.md`      | Traffic / Tickets FL wizard (3 paths: pay / school / contest)    | COMPLETE 2026-05-15     |
| 21 | `phases/source/PHASE_21_police_report.md` | Police Report Analyzer + new `scanner.py` agent                 | COMPLETE 2026-05-15     |
| 22 | `phases/source/PHASE_22_case_law.md`     | FL Case Law Lookup via CourtListener (RAG-only, sanctions guard) | COMPLETE 2026-05-15     |
| 23 | `phases/source/PHASE_23_packet_builder.md` | Mode A Filing Pipeline: PacketBuilder + PDF/A + EN/ES + $35 Stripe | COMPLETE 2026-05-15 — final phase |

### Part B notes

- **Hub tile count: 8.** Resolves the prior 6-vs-8 question. Order is
  fixed per Phase 15 source: `/upload`, `/small-claims`, `/expungement`,
  `/landlord`, `/forms`, `/traffic`, `/police-report`, `/case-law`.
- **Phase 23 is a single phase**, not a 9-way split. It carries
  `test_phase_23.py` (10 assertions) plus `test_full_v1.py` (4 assertions)
  inside the same source file.
- **EN/ES is Phase 23's responsibility**, not Phase 17's. Phase 23 ships
  pre-translated templates (`instructions_{en,es}.json`,
  `walkthrough_steps_{en,es}.json`, `cover_sheets/{type}_{en,es}.html`).
  Phase 12 already has the frontend EN/ES toggle; Phase 23 deepens it
  with backend-side templates.
- **$35 Stripe Filing Packet is Phase 23's responsibility**, not Phase 19's.
  Phase 23 attaches a new Stripe product via the existing Phase 09 webhook
  handler (adds a `checkout.session.completed` branch keyed on `packet_id`
  metadata). Phase 09 internals stay untouched.
- **Phase 23's `test_no_mode_b`** is the project's hardest gate. See
  Phase 11 divergence above — `florida_courts.py` will need either
  `# walkthrough text only` comments or deprecation before Phase 23 passes.
- **Repo state (reconciled 2026-06-05): Part B is 100% built + deployed.**
  All 8 tile pages (`.tsx`), all Part B routers, `scanner.py`, the 4 packet
  services, EN/ES templates, and `test_phase_15.py` are present and committed.
  `brutalist.css` was renamed to `frontend/src/styles/theme.css` in the
  documented v1 retheme (LEDGER lines 134-140) — not missing.
  `frontend/src/pages/ExpungementPage.jsx` remains as the orphaned multi-state
  predecessor; `/expungement` routes to `ExpungementFL.tsx`.

---

## Deployment (after Phase 23 passes)

Per `phases/source/PHASE_23_packet_builder.md`:

1. **Backend:** `uv sync` → commit → push to GitHub `main` → Railway
   auto-deploys `zesty-delight`.
2. **Frontend:** `npm run build` → commit → push → Railway auto-deploys
   `appealing-victory`.
3. **Stripe dashboard:** confirm "LegalClear Filing Packet" product at
   $35.00 is visible.
4. **Smoke test:** Hub → Small Claims tile → 5-step wizard → review with EN →
   Generate → FilingPacket → pay $35 with test card `4242 4242 4242 4242` →
   `?paid=1` → download ZIP → 3 PDFs inside → Walkthrough renders ≥8 steps
   for myflcourtaccess.com → enter test confirmation number → tracking
   page updates.

---

## Final report format

After Phase 23 passes its own tests AND `test_full_v1.py` passes, the
orchestrator emits **exactly** the report block defined at the bottom of
`phases/source/PHASE_23_packet_builder.md` and nothing outside it.
