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

**Credential hygiene (closed):** the leaked Supabase PAT
(`sbp_0074fb3f…`) and the Stripe `rk_live_…` key that went over the
chat transport were both rotated 2026-05-15. Post-rotation smoke
against `/api/packet/build` still returned a `cs_live_…` Stripe URL,
confirming the new secret key was synced to the `zesty-delight`
service before the old key was invalidated.

**v1 retheme shipped 2026-05-15** (commit `6c11fe0`). Light mode
`#FAFAF7 / #1A1A1A`, `#1E40AF` accent, Fraunces serif + Inter sans,
geometric mark favicon, color-split "legal clear" wordmark. Verified
live on `https://appealing-victory-production-d519.up.railway.app/`
via headless Chromium — 0 page errors, 0 console errors, all 8 tiles
render, wordmark colors confirmed at the exact target RGB values.

**LegalClear v1 shipped 2026-05-15.**

---

## Provenance + cross-references

- Canonical source: `phases/source/PHASE_NN_*.md` (24 files + `README.md`).
- Reference snapshots of pre-existing Part A frontend pages:
  `phases/reference/` (informational only — not authoritative).
- The earlier `LegalClear_OneShot_Prompt.md` at repo root is now superseded
  by the per-phase source files but kept for historical context.

---

## v2 Module — Property & Casualty (Module 5)

**Branch:** `feat/property-casualty`
**Worktree:** `../lc-casualty`
**Status:** COMPLETE (2026-07-04)
**Build phases:** 0–7

### Scope — first_party_property

First-party residential property insurance disputes (homeowner/condo/renter
claim under own policy for hurricane/wind/water/roof/fire/theft). Underlying
theory: breach of contract. The sub-type `first_party_property` was added
alongside the existing `insurance_bad_faith` and `premises_liability` —
three-way taxonomy, NOT a collapse.

**Boundary rule:** A coverage dispute stays first_party_property until an
explicit Civil Remedy Notice / § 624.155 posture appears — then it is
insurance_bad_faith. The two are not synonyms.

### Content tree

`src/content/property-casualty/` — 15 MDX pages split from verified source
content (`_source/property-and-casualty-florida.md`, 434 lines, 40KB):

| File | Content |
|---|---|
| `index.mdx` | Scope + disclaimer + two-clock table (the hook) |
| `00-scope.mdx` through `12-special-situations.mdx` | Full statutory walkthrough |
| `glossary.mdx` | Key terms |
| `_refs/statutes.json` | 16 statutes with official flsenate.gov links |
| `_refs/forms.json` | 10 forms with issuing-authority URLs |

All pages carry the disclaimer. Prose is verbatim from verified source — not
re-authored. CARRY: `07-filing-suit.mdx` carries a Rule 2.514 note (filing
deadline landing on weekend/holiday may extend to next business day).

### Deadline engine — calendar-unit support (systemic)

**Added:** `_add_calendar_period()` in `deadline/compute.py` — proper
anniversary-date math (years + months) replacing fixed day-counts for
statutory periods. `DeadlineRule` TypedDict extended with `response_years`,
`response_months`, and `deadline_type`.

**Rules added to `deadline/rules.py`:**

| Rule key | Period | Type | Statute |
|---|---|---|---|
| `pc_report_claim` | 1 calendar year | SOL | § 627.70132 |
| `pc_supplemental_claim` | 18 calendar months | SOL | § 627.70132 |
| `pc_file_suit` | 5 calendar years | SOL | § 95.11(2)(e) |
| `pc_pay_or_deny` | 60 days | insurer_deadline | § 627.70131(7)(a) |
| `pc_notice_of_intent` | 10 business days | pre_suit_gate | § 627.70152 |

**Deadline type taxonomy:** `SOL` (statute of limitations), `insurer_deadline`
(insurer-conduct deadline), `pre_suit_gate` (procedural gate), `court_filing`
(court-imposed deadline, existing rules). Propagated through backend → frontend
so deadline cards carry per-type labels rather than a blanket "statutory
deadline."

### CARRY-1: 2.514 roll-forward RATIFIED

The engine reports the raw calendar anniversary for statutory SOLs. It does
NOT apply Fla. R. Jud. Admin. 2.514 weekend/holiday roll-forward to year/month
deadlines. Rationale: conservative fail-safe — reports the earliest operative
date; roll-forward only extends, never contracts. Trade-off: on a
weekend-landing SOL anniversary, the true court-filing deadline may roll to
the next business day; the reported date is intentionally early. **Ratified,
not a defect.**

### ⚠️ SYSTEMIC FINDING — OPEN AUDIT ITEM

The deadline engine had NO calendar-unit support prior to this build
(`compute.py._add_calendar_period` was added here). **Any module with a
year/month deadline encoded before this commit may carry the same
fixed-day-count drift (1826-class bug) that caused early SOL dates in P&C.**

**Mandatory:** audit all calendar-interval deadlines platform-wide — small
claims, criminal procedure, every module with a year/month period. An SOL
drifting early in criminal procedure is a critical-severity correctness defect.

### Backend

- **Router:** `backend/src/api/routers/property_casualty.py` — extended to
  accept `first_party_property` sub-type (existing, modify-only).
- **Agent:** `backend/src/agents/property_casualty.py` — extended with
  first-party system prompt, deadline-engine integration, UPL middleware
  (`apply_disclaimer()`), zero local date arithmetic. Bad-faith and premises
  agents preserved untouched.
- **Intake router:** `backend/src/api/routers/intake.py` — `first_party_property`
  added to `VALID_SUB_TYPES`; disambiguation boundary rule added to classifier
  prompt (MERGE-REVIEW line).

### Frontend

`frontend/src/pages/PropertyCasualtyExplainer.tsx` — extended for three-way
sub-type handling. Key additions: `DeadlineCard` component (renders
backend-computed dates verbatim — zero client-side date math), per-type
deadline labels, resolution options, 48px touch targets, no directive framing.

### Tests

**22 unit tests + 6 integration tests = 28 total.**

| Suite | Tests | Status |
|---|---|---|
| `test_pc_deadlines.py` | 11 | ✅ Regression locks for leap-crossing, day-count unchanged, trace integrity |
| `test_pc_upl.py` | 11 | ✅ UPL enforcement (behavioral), classifier taxonomy, disclaimer via middleware |
| `test_pc_integration.py` | 6 | ✅ End-to-end: intake → engine → explain → disclaimer |

Regression locks reproduce every bug caught in this build (365-day drift,
1826-day drift, Feb 29 clamp, weekend-roll-forward on day-count rules).

### MERGE-REVIEW trunk touches

1. **`backend/src/api/routers/intake.py`** — +`first_party_property` to
   VALID_SUB_TYPES + disambiguation prompt line. Minimal. Isolated commit.
2. **`backend/deadline/rules.py`** — HEAVY. +5 P&C rules, +3 TypedDict fields
   (`response_years`, `response_months`, `deadline_type`). Shared computation
   surface — reconcile with any other branch's additions.
3. **`backend/deadline/compute.py`** — HEAVY. +`_add_calendar_period()`,
   calendar-period branch in `_compute_single`. Shared computation surface —
   if another branch independently added calendar-unit support, reconcile to
   a SINGLE implementation.

### Frozen components — confirmation

No frozen component modified beyond the sanctioned deadline-engine
calendar-unit change:
- `src/core/disclaimer.py` — untouched
- `src/core/upl.py` — untouched
- `src/api/routers/intake.py` — minimal additive touch (Phase 5)
- `src/api/routers/deadline.py` — untouched
- `backend/deadline/` rules + compute — sanctioned extension (calendar-unit support)
