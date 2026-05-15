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

### Part A — repo-vs-source divergences (must surface before Part B starts)

1. **Phase 0** — source verify expects `backend/pyproject.toml` (`uv` project
   file). Repo has only `backend/requirements.txt`. Phase 22 and Phase 23 source
   specs run `uv add httpx`, `uv add pikepdf jinja2` — these require
   `pyproject.toml` to exist. **This is a hard Part B blocker.** Decision
   pending: introduce `backend/pyproject.toml` (one-time scaffold fix, not
   a Part A rebuild) before Phase 15 begins.
2. **Phase 2** — source path is `backend/src/services/pdf_processor.py`. Repo
   has it at `backend/src/ingestion/` instead. Functional, but Phase 21 source
   imports `from ..services.pdf_processor import extract` — the import path
   will break unless the Phase 21 import is adjusted to `from ..ingestion...`
   or the file is moved/re-exported under `services/`.
3. **Phase 10** — source uses `/api/*` prefix on every endpoint
   (`/api/upload`, `/api/chat`, `/api/eligibility`, `/api/stripe/webhook`,
   `/api/push/register`). Repo serves the same logical endpoints at bare
   paths (`/upload`, `/chat/{document_id}`, `/eligibility`, `/webhook`).
   **Not a Part B blocker** — every Part B router declares its own
   `prefix="/api/..."`, so Part B endpoints will be at `/api/*` regardless.
   Part A bare-path endpoints stay as-is; the frontend already knows them.
4. **Phase 11** — `backend/src/platforms/florida_courts.py` contains 5
   `myflcourtaccess` references with NO `# walkthrough text only` comment.
   Phase 23's `test_no_mode_b` would fail today. Source Phase 11 explicitly
   says "Phase 23 may deprecate `florida_courts.py` to a thin wrapper or
   remove it" — Phase 23 resolves this. **Not a Part A fix; Phase 23 work.**
5. **Phase 12** — source builds `.tsx` (TypeScript). Repo is 100% `.jsx`,
   zero `.tsx`. Phase 15 source creates new files as `.tsx`. **Vite config
   must accept .tsx by Phase 15.** Decision pending: convert to TS at
   Phase 15 boundary, or rewrite Phase 15 deliverables as `.jsx`. Source
   wins → introduce TS.
6. **Phase 13** — source says mobile is built (`mobile/App.tsx`,
   `mobile/app.json`). Repo `mobile/` is empty. Source policy: "Note it in
   the final report but do NOT block. Mobile is deferred." Phase 13 source
   is explicit: "**Mobile work is OUT OF SCOPE for Phases 15–23.**" So
   empty `mobile/` is a documented Part A gap, not a Part B blocker.

---

## Part B — phases 15-23 — BUILD TARGET — HARD STOP UNTIL DIVERGENCES RESOLVED

Each phase's full spec (deliverables, code blocks, test, pass criteria) lives
in the source file. The orchestrator builds the phase per the source, runs
its `test_phase_NN.py`, and marks the row COMPLETE only when every assertion
in the source passes.

| #  | Source file                              | Title                                                            | Status                  |
|----|------------------------------------------|------------------------------------------------------------------|-------------------------|
| 15 | `phases/source/PHASE_15_hub_restructure.md` | Hub Restructure + Brutalist Design System (8-tile HomeHub)    | PENDING                 |
| 16 | `phases/source/PHASE_16_small_claims.md` | Small Claims FL 5-step wizard + 67-county data                   | PENDING                 |
| 17 | `phases/source/PHASE_17_expungement_ui.md` | Expungement FL UI: 5-question quiz + `/api/expungement/*`      | PENDING                 |
| 18 | `phases/source/PHASE_18_landlord_tenant.md` | Landlord/Tenant FL: 3 sub-flows (deposit / repairs / eviction) | PENDING                 |
| 19 | `phases/source/PHASE_19_forms_finder.md` | Court Forms Finder FL (frontend-only, data-driven, ≥18 entries)  | PENDING                 |
| 20 | `phases/source/PHASE_20_traffic.md`      | Traffic / Tickets FL wizard (3 paths: pay / school / contest)    | PENDING                 |
| 21 | `phases/source/PHASE_21_police_report.md` | Police Report Analyzer + new `scanner.py` agent                 | PENDING                 |
| 22 | `phases/source/PHASE_22_case_law.md`     | FL Case Law Lookup via CourtListener (RAG-only, sanctions guard) | PENDING                 |
| 23 | `phases/source/PHASE_23_packet_builder.md` | Mode A Filing Pipeline: PacketBuilder + PDF/A + EN/ES + $35 Stripe | PENDING — final phase |

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
- **Repo state: Part B is 0% built.** Zero new frontend pages, zero new
  backend routers, zero new services, zero new templates, zero new tests.
  `frontend/src/pages/ExpungementPage.jsx` exists but is a multi-state
  design that predates Phase 17's FL-only quiz — it is not a Phase 17
  deliverable.

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
