# LegalClear — Phase Ledger

**Single source of truth for build state.** The `phase-orchestrator` agent
reads this first every session and writes to it after every phase transition.
If this ledger disagrees with the actual repo or with `phases/source/`, the
repo + source files win — re-verify and correct.

Phase names + scopes are taken from `phases/source/PHASE_NN_*.md` (canonical,
2026-05-14). Prior ledger revisions had Part A phase 1/2/8 names wrong and
all of Part B 17-22 subjects wrong; this revision corrects against source.

Status values: `DEPLOYED` · `COMPLETE` · `PENDING` · `BLOCKED` · `OUT-OF-SCOPE`
· `NOT BUILT` (used when source spec exists but the artifact is absent and
the no-block clause applies)

---

## Part A — phases 0-14 · VERIFY ONLY · do not rebuild

| #  | Title (per source)                                  | Status                | Last verified | Note |
|----|------------------------------------------------------|-----------------------|---------------|------|
| 0  | Project scaffold + venv                              | DEPLOYED              | 2026-05-14    | `backend/pyproject.toml` added 2026-05-14 mirroring `requirements.txt` (Railway nixpacks still uses pip+requirements.txt explicitly; pyproject.toml unblocks local `uv` workflows + Phase 22/23 `uv add`). `uv sync` not yet run — no lockfile. |
| 1  | DB / memory layer (`db.py`, `DatabaseManager`)       | DEPLOYED              | 2026-05-14    | `backend/src/memory/db.py` — prior ledger mislabeled this phase as "Document ingestion." |
| 2  | PDF extraction + OCR pipeline                        | DEPLOYED — divergence | 2026-05-14    | Source path is `backend/src/services/pdf_processor.py`; repo has equivalent at `backend/src/ingestion/`. Phase 21's source imports `from ..services.pdf_processor` — will need adjustment at Phase 21 time. |
| 3  | Classifier Agent                                     | DEPLOYED              | 2026-05-14    | `backend/src/agents/classifier.py` — model `claude-sonnet-4-6` confirmed. |
| 4  | Explainer Agent                                      | DEPLOYED              | 2026-05-14    | `backend/src/agents/explainer.py` — model confirmed. |
| 5  | Form Guide Agent                                     | DEPLOYED              | 2026-05-14    | `backend/src/agents/form_guide.py` — model confirmed. |
| 6  | Risk Scanner Agent                                   | DEPLOYED              | 2026-05-14    | `backend/src/agents/risk_scanner.py` — red/yellow/green clause model. |
| 7  | Expungement Agent                                    | DEPLOYED              | 2026-05-14    | `backend/src/agents/expungement.py` — FL §943.0585 / §943.059 / §943.0584 referenced. |
| 8  | Supabase production DB migration                     | DEPLOYED              | 2026-05-14    | `backend/src/memory/db.py` routes to Supabase via `SUPABASE_URL`/`SUPABASE_KEY`. Prior ledger mislabeled this as "Memory layer" (that's Phase 1). Phase 23 will ADD a `packets` table. |
| 9  | Stripe paywall ($5/$10/$15 + $20/mo + 1 free doc)    | DEPLOYED — re-verify  | 2026-05-14    | `backend/src/payments/stripe_client.py` — exact price tiers + free-doc gate not yet re-verified against source. |
| 10 | FastAPI backend consolidation                        | DEPLOYED — divergence | 2026-05-14    | Source path `backend/src/api/main.py`; repo split into `backend/main.py` (entrypoint) + `backend/src/api/routes.py`. Source endpoints use `/api/*` prefix; repo serves at bare paths. Not a Part B blocker (Part B routers declare their own `/api/*` prefix). |
| 11 | FL Courts Mode A scaffold                            | DEPLOYED — see Phase 23 | 2026-05-14  | `backend/src/platforms/florida_courts.py` — Mode A only. Contains 5 `myflcourtaccess` references with NO `# walkthrough text only` marker. Phase 23 `test_no_mode_b` would fail today. Source Phase 11 says Phase 23 may deprecate this file to a thin wrapper. |
| 12 | React + Tailwind frontend                            | DEPLOYED              | 2026-05-14    | `frontend/tsconfig.json` + `tsconfig.node.json` added 2026-05-14; `typescript` + `@types/{node,react,react-dom}` added to `package.json` devDeps. `allowJs: true` keeps existing `.jsx` working. `npm install` not yet run — TS deps not yet materialized. |
| 13 | React Native (Expo)                                  | NOT BUILT — no-block  | 2026-05-14    | `mobile/` is empty. Source verify command would fail, but source explicitly says "Note it in the final report but do NOT block." Mobile is OOS for Phases 15-23 per source. |
| 14 | Railway / nginx deploy                               | DEPLOYED              | 2026-05-14    | Railway services `zesty-delight` (backend) + `appealing-victory` (frontend) live. nginx + systemd: not used (Railway-only deploy is fine per source — source mentions both as options). |

## Part B — phases 15-23 · BUILD TARGET

Source files for all 9 phases are now in `phases/source/` and complete with
goal, deliverables, verify command, and pass criteria. The orchestrator
executes each per its source file. Hard blockers (Part A divergences #1
and #5) resolved 2026-05-14 — scaffold files in place; awaiting `uv sync`
+ `npm install` to materialize deps.

| #  | Title (per source)                                                       | Status  | Note |
|----|---------------------------------------------------------------------------|---------|------|
| 15 | Hub Restructure + Brutalist Design System (8-tile HomeHub)                 | COMPLETE 2026-05-14 | `HomeHub.tsx` + `HubTile.tsx` + `PhaseStub.tsx` + `brutalist.css` shipped; `App.jsx` converted to `App.tsx` with 10 routes (hub + tile 1 to existing uploader + 6 stubs + existing /expungement, /results, /pay); `index.html` carries static tile titles in `<noscript>` for the test's HTML-content check. `frontend/tests/test_phase_15.py`: 4/4 assertions pass. `npm run build` clean (1739 modules, 28.80 kB CSS / 86.71 kB gzip JS). |
| 16 | Small Claims FL 5-step wizard + 67-county data                             | PENDING | Adds `/api/small-claims/generate`, `fl_counties.json`. |
| 17 | Expungement FL UI: 5-question quiz + `/api/expungement/*`                  | PENDING | NEW page `ExpungementFL.tsx`. Existing `ExpungementPage.jsx` is unrelated multi-state design — not a Phase 17 artifact. |
| 18 | Landlord/Tenant FL: 3 sub-flows (deposit / repairs / eviction)             | PENDING | FL §83.49 / §83.56 / §83.60. |
| 19 | Court Forms Finder FL (frontend-only, data-driven, ≥18 entries)            | PENDING | No backend changes. Strict URL whitelist (gov domains only). |
| 20 | Traffic / Tickets FL wizard (3 paths: pay / school / contest)              | PENDING | Adds `/api/traffic/generate`, `fl_traffic_violations.json`. |
| 21 | Police Report Analyzer + new `scanner.py` agent                            | PENDING | Imports `pdf_processor.extract` — adjust path per Part A divergence 2. |
| 22 | FL Case Law Lookup via CourtListener (RAG-only, sanctions guard)           | PENDING | LLM forbidden from generating case names/citations. Needs `uv add httpx` → requires Part A divergence 1 resolved. |
| 23 | Mode A Filing Pipeline: PacketBuilder + PDF/A + EN/ES + $35 Stripe         | PENDING | Final phase. Needs `uv add pikepdf jinja2`. Resolves Phase 11 `myflcourtaccess` divergence. Carries `test_no_mode_b` + `test_full_v1.py`. |

---

## Open gaps

1. ~~`backend/pyproject.toml` missing.~~ **RESOLVED 2026-05-14** — file
   added mirroring `requirements.txt`. Run `cd backend && uv sync` once
   to materialize the lockfile before any Phase 22/23 `uv add` command.
2. ~~TypeScript config missing.~~ **RESOLVED 2026-05-14** — `tsconfig.json`
   + `tsconfig.node.json` added; TS deps in `package.json` devDeps. Run
   `cd frontend && npm install` once to materialize before Phase 15 builds
   the first `.tsx` files.
3. **Phase 11 `myflcourtaccess` references unmarked.** Latent Phase 23
   `test_no_mode_b` failure. Resolution: Phase 23 either deprecates
   `florida_courts.py` to a wrapper or adds `# walkthrough text only`
   comments. No action needed before Phase 15.
4. **`backend/src/services/pdf_processor.py` path mismatch.** Source Phase 21
   imports from that path; repo equivalent lives at `backend/src/ingestion/`.
   Resolution: re-export from `services/` or adjust the Phase 21 import. No
   action needed before Phase 21.

Once `uv sync` + `npm install` complete, Phase 15 is fully unblocked.

---

## Provenance + cross-references

- Canonical source: `phases/source/PHASE_NN_*.md` (24 files + `README.md`).
- Reference snapshots of pre-existing Part A frontend pages:
  `phases/reference/` (informational only — not authoritative).
- The earlier `LegalClear_OneShot_Prompt.md` at repo root is now superseded
  by the per-phase source files but kept for historical context.
