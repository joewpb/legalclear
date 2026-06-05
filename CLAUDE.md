# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LegalClear is a Florida legal-information platform for self-represented (pro se) users. Users upload court documents; the platform classifies them, extracts deadlines via a two-stage pipeline (LLM extraction → deterministic computation), explains them in plain language, surfaces relevant FL court forms, and schedules reminders. Additional tools: Small Claims wizard, Eviction defense, Traffic citation wizard, Police Report Analyzer, FL Case Law Lookup, Filing Packet builder.

**The product produces legal information, never legal advice.** LLMs extract; deterministic code computes. No model ever outputs a computed deadline date.

## Commands

### Backend (Python / FastAPI)

```bash
cd backend
uv sync                                          # install deps
uv run uvicorn src.api.routes:app --port 8001 --reload   # dev server

# Tests — run from backend/
uv run pytest tests/                             # full suite
uv run pytest tests/test_deadline_compute.py     # single file
uv run pytest tests/test_upl.py -k "test_name"  # single test

# Eval harness
uv run python -m evals.run_all                   # fast mode (no LLM, CI-safe)
uv run python -m evals.run_all --full            # full pipeline with LLM
uv run python -m evals.run_all --id CS-001       # single document
```

**Hard constraint: backend runs on port 8001. Port 8000 is a build failure.**

### Frontend (React / TypeScript / Vite)

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run build        # production build
npm run type-check   # tsc --noEmit
```

### Database (Supabase)

Migrations live in `supabase/migrations/`. Never run migrations directly against production without first verifying on a Supabase development branch. Additive-only changes (new columns with defaults, new tables) can go direct; any DDL that drops or restructures must go through a branch.

## Architecture

### Request flow

```
Client (React / React Native)
  → Railway backend (FastAPI, zesty-delight, :8001)
    → Supabase Postgres 17 (miedifclpqewnixxkahs, us-west-2)
    → Anthropic API (Claude)
    → Stripe
```

The client talks only to the Railway backend. The backend is the sole holder of `SUPABASE_SERVICE_KEY` (service-role, bypasses RLS). Every backend query over user data must be explicitly scoped to the authenticated user — RLS is a second line of defense, not the first.

### Backend structure (`backend/src/`)

| Package | Role |
|---|---|
| `api/routes.py` | FastAPI app; registers all routers; singleton agents wired here |
| `api/routers/` | One router per feature (deadline, triage, analysis, forms, law, reminders, small_claims, landlord, traffic, expungement, police_report, case_law, packet) |
| `agents/` | Claude-backed agents: classifier, explainer, form_guide, risk_scanner, scanner (police report), expungement, case_context |
| `core/` | Config (Settings from env), UPL wall, escalation router, disclaimer texts (EN/ES), i18n, notifications |
| `ingestion/` | PDF parser, OCR, text cleaner — entry point is `ingest_document()` |
| `memory/db.py` | `DatabaseManager` wraps supabase-py with service-role key |
| `payments/` | Stripe client + `check_access()` guard |
| `services/` | Packet builder, PDF/A generator, translation layer, county router |
| `platforms/` | Florida courts helpers, notifications |

Top-level packages (outside `src/`):

| Package | Role |
|---|---|
| `deadline/` | Two-stage deadline pipeline: `extract.py` (LLM Stage 1) + `compute.py` (deterministic Stage 2) + `rules.py` (8 FL rules) + `pipeline.py` (orchestrator, writes to DB) |
| `triage/` | Document type classifier (13 types); `router.py` contains `ALWAYS_ESCALATE_TYPES` |
| `evals/` | 50-document eval set; `ground_truth.json` is locked — never edit it to pass a test |

### Frontend structure (`frontend/src/`)

React + TypeScript + Vite + Tailwind. Routing via `react-router-dom`. i18n via `react-i18next` (EN/ES). Stripe via `@stripe/react-stripe-js`.

```
src/
  App.tsx            # Router root
  api.js             # Axios wrapper to backend
  pages/             # Top-level route pages
  components/        # Feature components grouped by tool:
    layout/          # Shell, nav
    smallclaims/     # Small Claims wizard
    landlord/        # Eviction defense
    traffic/         # Traffic citation wizard
    policereport/    # Police Report Analyzer (includes CaseContextBanner)
    caselaw/         # FL Case Law Lookup
    packet/          # Filing Packet builder
    expungement/     # Expungement flow
```

All API keys are server-side only. New files use `.tsx`/`.ts`; legacy `.jsx` files are not migrated unless a phase explicitly requires it.

### UPL / escalation layer

`core/upl.py` enforces two invariants on every user-facing output:
1. Every output carries a disclaimer (legal information ≠ legal advice), in EN or ES.
2. High-stakes situations (criminal charges, restraining orders, fatal-severity deadlines with confidence < 0.90) escalate to attorney referral instead of answering.

`core/escalation.py` classifies document types into `_STANDARD`, `_ELEVATED`, and `_CRIMINAL` tiers.

### Deadline engine invariant

LLMs extract trigger events (event type, trigger date, service method). Deterministic code in `deadline/compute.py` does all calendar arithmetic under Florida Rules (§2.514, court closures). Every deadline carries a `computation_trace` with rule citations. This split is a hard constraint — never add date arithmetic to an LLM prompt.

## Phase system

- `phases/V2_LEDGER.md` — authoritative v2 phase state; read it at the start of each v2 session.
- `phases/LEDGER.md` — v1 state (phases 0–23, all complete and deployed).
- `phases/BUILD_PLAN.md` — v2 phase sequence and Definitions of Done.
- Phases execute one per session in strict order. Print `PHASE N COMPLETE` only after every DoD assertion passes. If a phase's verification fails twice, print `PHASE N BLOCKED — <error>` and halt.

## Deploy

| Surface | Railway service | Build command |
|---|---|---|
| Backend | `zesty-delight` | `uv sync` → push |
| Frontend | `appealing-victory` | `npm run build` → push |

Stripe product: **"LegalClear Filing Packet"** — $35.00.

## CI

Three GitHub Actions workflows:
- **node.js.yml** — `npm ci && npm run build && npm test` on Node 22.x (from `frontend/`)
- **eval-deadline.yml** — `uv run python -m evals.run_all` (fast mode, no LLM); triggers on changes to `backend/deadline/`, `backend/triage/`, or `backend/evals/`
- **gitleaks.yml** — secret scan on every push/PR

All workflows use `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true`.

## Key constraints

- Use `uv` for all Python env/package operations — never `pip` or `venv` directly.
- `/api/upload` is complete and correct — do not modify it.
- Every user-facing string accepts a `language` parameter; EN ships first, ES must not require re-architecture.
- Forms whose change-detection status is unresolved are gated, not served silently.
- `backend/.env.example` has all required env var names with placeholder values.
