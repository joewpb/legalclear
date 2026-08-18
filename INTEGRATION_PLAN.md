# LegalClear — Feature-to-Surface Audit + Integration Plan (REBUILT)

**Rebuilt:** 2026-08-17 against main @ `f145dd8` (Phase H).
**Why rebuilt:** this corrects **audit finding 7** — the 2026-07-06 version of this
file was materially stale: it listed the analysis router and the top-level
`/eligibility` route as existing (both deleted in Phase G), listed five dead
frontend components as deletion candidates (deleted), described Upload,
Expungement, Landlord, Traffic, and Case Law as ORPHANED (all now have HomeHub
tiles), and flagged auto-fire / hardcoded-key defects that have since been fixed.
**Deployed frontend:** https://legalclear.app (Railway `appealing-victory`)
**Deployed backend:** Railway `zesty-delight` (:8001)

The authoritative capability-by-capability state now lives in `SPEC_LEDGER.md`
(mechanically checked by `make verify-docs`). This file records surface state and
the standing integration/UPL rules.

---

## CONFIRMED STATE (do not re-litigate)

- Phases A–F of `REMEDIATION_PLAN.md` complete; gates G1–G5 closed. Phase G
  (cleanup) merged 2026-08-17. Backend unit-suite baseline: **352 passed, 1 skipped**
  (CI scope per `.github/workflows/pytest.yml`).
- **Property & Casualty remains the reference implementation for "done":** input
  surface → explicit submit → streamed result → UPL disclaimer on every render.
- The three Small Claims defects from the 2026-07-06 audit (mount auto-fire,
  URL-param-only input, hardcoded `testkey123` in the bundle) were fixed in the
  Phase 2 remediation (P2.0.a–d); the auto-fire rule and key handling are covered
  by the standing rules below.
- Payments are **disabled, not deleted** (Decision 1): `PAYMENTS_ENABLED` off,
  gating code retained, `backend/tests/test_payments_disabled.py` asserts it.

---

## Feature surface table (fact-checked against the tree at f145dd8)

Legend: **Nav** = reachable from HomeHub tile or a live page. Frontend routes are
from `frontend/src/App.tsx`; tiles from `MODULE_TILES` in
`frontend/src/pages/HomeHub.tsx` (14 tiles).

| # | Feature | Backend route(s) | Frontend route | Nav | Status |
|---|---|---|---|---|---|
| 1 | Property & Casualty | `/api/property-casualty/explain` | `/property-casualty` | tile ✓ | LIVE (reference) |
| 2 | Wills & Trusts | `/api/wills-trusts/explain` | `/wills-trusts` | tile ✓ | LIVE |
| 3 | Police Report Analyzer | `/api/police-report/analyze`, `/analyze/batch` | `/police-report` | tile ✓ | LIVE |
| 4 | Discovery Motion Analyzer | `/api/discovery/analyze` | `/discovery-motion` | tile ✓ | LIVE |
| 5 | Forms Finder | `/api/forms/*` | `/forms` | tile ✓ | LIVE |
| 6 | Small Claims Explainer + Filing Wizard | `/api/small-claims/*` | `/small-claims`, `/small-claims/file` | tile ✓ | LIVE |
| 7 | Criminal Procedure Explainer | `/api/criminal/explain` | `/criminal-procedure` | tile ✓ | LIVE |
| 8 | Upload, Triage & Deadline Engine (CORE) | `/upload`, `/process/{id}`, `/api/deadline/*` | `/upload`, `/results/:documentId` | tile ✓ | LIVE |
| 9 | Expungement (FL) | `/api/expungement/eligibility`, `/generate` | `/expungement` | tile ✓ | LIVE |
| 10 | Landlord / Tenant Defense | `/api/landlord/*` | `/landlord/*` | tile ✓ | LIVE |
| 11 | Traffic Citation Wizard | `/api/traffic/generate` | `/traffic` | tile ✓ | LIVE |
| 12 | Case Law Lookup (deterministic — ADR-1) | `/api/case-law/search` | `/case-law` | tile ✓ | LIVE |
| 13 | Attorney Referral | `/api/attorney-referral/*` | `/attorney-referral` | tile ✓ | LIVE |
| 14 | Find Legal Help | (county data) | `/find-legal-help` | tile ✓ | LIVE |
| 15 | Filing Packet ($35 Stripe) | `/api/packet/*` | `/filing-packet/:packetId` | from generate flows | LIVE (paywall DARK per Decision 1) |
| 16 | Paywall / Checkout | `/subscribe/{user_id}`, `/webhook` | `/pay/:documentId` | from `/upload` | DARK (Decision 1) |
| 17 | Chat Expert drawer | `/api/chat/{module}` | (drawer, no route) | on live pages | LIVE |
| 18 | AI Intake | `/api/intake` | powers HomeHub | ✓ | LIVE |
| 19 | Law reference | `/api/law/*` | none | — | HEADLESS (intentional — internal: deadline engine + case law) |
| 20 | Reminders | `/api/reminders/process` | none | — | HEADLESS (intentional — pg_cron); email adapter DARK until provider key (Decision 8) |
| 21 | Triage router | `/api/triage/classify`, `/confirm` | none (0 consumers) | — | **AMBIGUOUS** — Joe decision pending (retire vs wire); `/upload` classifies inline in `routes.py`. Do not touch. |

### Removed in Phase G (no longer in the tree — must not be listed as live)

| Former item | Disposition |
|---|---|
| Analysis router (`/api/analyze/*`, `routers/analysis.py`) | **Deleted** (S2-6). 0 consumers. |
| Push-token endpoint + `save_push_token` + `mobile/` submodule | **Deleted** (Decision 9: mobile DEFERRED). `push_tokens` **table** drop is authored but HELD on unmerged branch `fix/g2-push-tokens-table-drop`. |
| Top-level `POST /eligibility` | **Deleted** — superseded by `/api/expungement/eligibility`. |
| `AnalysisDashboard.jsx`, `LandingPage.jsx`, `ExpungementPage.jsx`, `PhaseStub.tsx`, `layout/Navbar.jsx` | **Deleted** dead frontend components. |
| `get/set_user_supplied_service_date` helpers; `trigger_events.user_*` columns | **Deleted/dropped** (B5-f3 successor: `document_service_facts` table — see ADR-3 in `docs/ADRS.md`). |

---

## Integration order (standing rules for any future surfacing work)

1. **Copy the P&C pattern** for any newly surfaced module: input surface →
   explicit submit → streamed result → UPL disclaimer on every render.
2. **No LLM call without explicit user action. Ever.** No `useEffect`-on-mount may
   hit an `/explain|/generate|/analyze` endpoint. Re-run the auto-fire sweep after
   any new page lands.
3. **No secrets in the client bundle.** No static `X-API-Key` fallback in frontend
   code; keys are server-side only.
4. **Ledger-first:** a new capability gets a `SPEC_LEDGER.md` row (and a spec)
   before code; `make verify-docs` must pass in the same commit.
5. **Migrations only through CI** (`.github/workflows/migrate.yml`); parity checked
   by `.github/workflows/parity.yml` + `scripts/parity_check.py`.

### Next planned work (recorded, not dispatched)

- **Phase I — P&C Claim Guide module: NOT BUILT.** Recorded 2026-08-15 in
  `REMEDIATION_PLAN.md`; not scoped, not dispatched. The referenced spec path
  (`docs/pc-claim-guide-module.md`) does **not exist** in the tree at f145dd8 —
  writing that spec is the first task of any Phase I dispatch.
- **Triage router decision** (retire vs wire) — Joe.
- **`push_tokens` table drop** — merge or discard branch `fix/g2-push-tokens-table-drop` — Joe.
- **Email provider key** (Decision 8; recommendation Resend) — Joe.

---

## UPL guardrails (non-negotiable, every module)

Per `backend/src/core/upl.py` invariants:
1. Every user-facing output carries the disclaimer (legal information ≠ legal
   advice), EN and ES, from the single canonical source `apply_disclaimer`
   (Decision 3 — `get_disclaimer` and inline texts are superseded).
2. High-stakes situations (criminal charges, restraining orders, fatal-severity
   deadlines with confidence < 0.90) escalate to attorney referral instead of
   answering (`backend/src/core/escalation.py`).
3. **No LLM ever outputs a computed deadline date.** All calendar arithmetic lives
   in `backend/deadline/compute.py` with a `computation_trace`.
4. **No external links in generated output** — deterministic strip at the boundary
   (`backend/src/core/url_filter.py`, Decision 4).
5. Errors after substantive content has streamed must still carry the disclaimer
   (Decision 5); bare error envelopes need none.

---

## Out of scope for this document

- Payments re-enablement (Decision 1 keeps the code; turning it back on is a
  product decision, not an integration task).
- Mobile app (DEFERRED, Decision 9).
- ES opinion corpus (backlog; ES honesty stamp ships instead).
