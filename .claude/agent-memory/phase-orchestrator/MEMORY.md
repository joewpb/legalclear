# phase-orchestrator — MEMORY.md

Persistent cross-session state for the LegalClear build. Reflects
`phases/LEDGER.md`; the ledger is canonical, this is continuity. Keep concise.

## Project
LegalClear — pay-per-use legal document analysis. Phased build, 24 phases (0-23).
Part A (0-14) deployed. Part B (15-23) is the build target.

## Current state (seed — re-verify on first run)
- Part A phases 0-14: deployed, NOT yet verified by this agent. First job is a
  Part A verification sweep.
- Part B phases 15-23: all PENDING.
- Phases 10-14: STUB — names/specs unknown, must be reconstructed from the repo.
- Phases 15-23: scope reconstructed from the v1 smoke test, not the verbatim
  source — confirm each against the original build prompt before executing.

## Key facts (do not rediscover)
- Backend FastAPI on port 8001. Port 8000 for the app = build failure.
- Frontend React on 3000. Mobile is React Native.
- DB is Supabase (production). Payments via Stripe. Python via `uv`.
- Deploy: Railway — backend `zesty-delight`, frontend `appealing-victory`.
- Stripe product: "LegalClear Filing Packet" at $35.00. Languages: en, es.
- `/api/upload` exists and is correct — never touch it.
- Mode B automation anywhere in `backend/src/` = fail the build.
- Existing agent pipeline: classifier → explainer → form guide → risk scanner.
- `florida_courts.py` exists in Mode A form (Part B Phase 20 builds on it).

## Next action
Run the session-start protocol: read AGENTS.md + LEDGER.md + PHASE_SPECS.md,
reconcile against the repo, then begin the Part A verification sweep
(delegate to Explore). Resolve the 10-14 stubs before touching Part B.

## Open blockers
None yet. Stub rows for 10-14 must be resolved before execution passes phase 9.
