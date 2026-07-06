# LegalClear — Feature-to-Surface Audit + Integration Plan

**Date:** 2026-07-06
**Scope:** Read-only audit of every backend router and frontend route, classify each feature by surface state, and produce a phased integration plan for everything that is ORPHANED / HEADLESS / HOLLOW. Paywall/Stripe features are audited but **out of scope** for the plan.
**Deployed frontend:** https://legalclear.app
**Deployed backend:** Railway service `zesty-delight` (:8001)

---

## CONFIRMED STATE (do not re-litigate)

- **Property & Casualty (Module 5)** — FULLY SURFACED and verified live. Date-of-loss field renders on first load (PR #24). Backend deadline engine returns §627.70132 references. **P&C is the reference implementation for "done"** — every newly surfaced module should copy its pattern: input surface → explicit submit → streamed result → UPL disclaimer.
- **Small Claims Explainer (`/small-claims`)** has THREE confirmed defects:
  - **(a)** `useEffect` on mount auto-fires `POST /api/small-claims/explain` on every visit (`SmallClaimsExplainer.tsx:304-307`) — paid LLM call.
  - **(b)** No user input form. Entities read ONLY from URL query params (`SmallClaimsExplainer.tsx:236-239`). Page is unusable standalone.
  - **(c)** Hardcoded `X-API-Key: "testkey123"` in the client bundle (`SmallClaimsExplainer.tsx:260`), gating a paid LLM endpoint. Publicly scriptable cost exposure.

---

## PHASE 1 — AUDIT (the table is the artifact)

### Feature classification table

Legend: **Nav** = reachable from a live nav surface (HomeHub tile, header, or a live page). **Input UI** = page has its own user input affordance (not URL-param-only). **Auto-fire** = `useEffect` calls a paid LLM endpoint on mount with empty deps.

| # | Feature | Backend route(s) | Frontend route | Nav entry | Input UI | Auto-fires on mount | Status | Paywall? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Property & Casualty** (M5) | `/api/property-casualty/explain` | `/property-casualty` | HomeHub tile ✓ | Yes (4) | No | **SURFACED** (reference) | — |
| 2 | **Wills & Trusts** (M6) | `/api/wills-trusts/explain` | `/wills-trusts` | HomeHub tile ✓ | Yes (10) | No | **SURFACED** | — |
| 3 | **Police Report Analyzer** | `/api/police-report/analyze`, `/analyze/batch` | `/police-report` | HomeHub tile ✓ | Yes (file upload) | No | **SURFACED** | — |
| 4 | **Discovery Motion Analyzer** (M4) | `/api/discovery/analyze` | `/discovery-motion` | HomeHub tile ✓ | Yes (file upload) | No | **SURFACED** | — |
| 5 | **Forms Finder** | `/api/forms/*` | `/forms` | HomeHub tile ✓ | Yes (search, 6) | No (DB read only) | **SURFACED** ⚠️ hardcoded key | — |
| 6 | **Small Claims Explainer** (M1) | `/api/small-claims/explain`, `/generate` | `/small-claims` | HomeHub tile ✓ | **No** (URL params only) | **YES** ⚠️ cost leak | **HOLLOW** ⚠️ hardcoded key | — |
| 7 | **Criminal Procedure** (M2) | `/api/criminal/explain` | `/criminal-procedure` | HomeHub tile ✓ | **No** (URL params only) | **YES** ⚠️ cost leak | **HOLLOW** ⚠️ hardcoded key | — |
| 8 | **Upload, Triage & Deadline Engine** (CORE v1) | `/upload`, `/process/{id}`, `/api/deadline/*` | `/upload` | **None** (only dead v1 chrome) | Yes (UploadFlow) | No | **ORPHANED** ⚠️ hardcoded key | — |
| 9 | **Expungement (FL)** | `/api/expungement/eligibility`, `/generate` | `/expungement` | **None** (only via orphaned `/upload`→Results sidebar) | Yes (quiz) | No | **ORPHANED** | — |
| 10 | **Landlord / Tenant Defense** | `/api/landlord/{deposit,repairs,eviction}/generate` | `/landlord/*` | **None** | Yes (3 sub-flows) | No | **ORPHANED** | — |
| 11 | **Traffic Citation Wizard** | `/api/traffic/generate` | `/traffic` | **None** | Yes (wizard steps) | No | **ORPHANED** | — |
| 12 | **Case Law Lookup** | `/api/case-law/search` | `/case-law` | **None** | Yes (search) | No | **ORPHANED** | — |
| 13 | Small Claims Filing Wizard | (uses #6 `/generate`) | `/small-claims/file` | From #6 explainer ✓ | Yes (6 steps) | No | SURFACED (sub-page) | leads to #14 |
| 14 | **Filing Packet** (Stripe $35) | `/api/packet/*` | `/filing-packet/:packetId` | From generate flows ✓ | Yes | No (GET metadata) | SURFACED | **PAYWALL — out of scope** |
| 15 | Analysis Results | `/document/{id}`, `/process/{id}` | `/results/:documentId` | From `/upload` ✓ | — | No (DB read) | SURFACED (sub-page of #8) | — |
| 16 | Paywall / Checkout | `/subscribe/{user_id}`, `/webhook` | `/pay/:documentId` | From `/upload` ✓ | — | No | SURFACED | **PAYWALL — out of scope** |
| 17 | **Chat Expert** (per-module drawer) | `/api/chat/{module}` | (drawer, no route) | Rendered on 5 live pages ✓ | Yes | No | SURFACED (drawer) | **PAYWALL — out of scope** |
| 18 | **Law reference** (statutes/rules/closures) | `/api/law/*` | none | — | — | — | **HEADLESS** (intentional — internal: deadline engine + case law) | — |
| 19 | **Reminders** | `/api/reminders/process` | none | — | — | — | **HEADLESS** (intentional — server pg_cron) | — |
| 20 | **Triage router** | `/api/triage/classify`, `/confirm` | none (0 consumers) | — | — | — | **HEADLESS** (unused — `/upload` classifies inline via `routes.py`, not this router) | — |
| 21 | **Analysis router** | `/api/analyze/{id}`, `/analyze/stream/{id}` | none (0 consumers) | — | — | — | **HEADLESS** (unused) | — |
| 22 | Top-level eligibility | `/eligibility` | none (0 consumers) | — | — | — | **DARK** (dead — superseded by `/api/expungement/eligibility`) | — |
| 23 | Intake router (M0) | `/api/intake` | consumed by HomeHub ✓ | — | — | — | SURFACED (powers hub) | — |

**Dead frontend code (not routed, not imported by any live route) — DARK, candidates for deletion:**
- `pages/AnalysisDashboard.jsx` (references unrouted `/dashboard`)
- `pages/LandingPage.jsx` (references unrouted `/dashboard`)
- `pages/ExpungementPage.jsx` (replaced by `ExpungementFL`; App.tsx:55 confirms)
- `pages/PhaseStub.tsx`
- `components/layout/Navbar.jsx` (App renders `SiteHeader`, not `Navbar` — the old nav linking `/upload`, `/dashboard` is dead)

**Broken link from a LIVE component:** `ChatDrawer.tsx:624` → `window.location.href = "/upgrade"`. `/upgrade` is **not a routed page**. (Paywall-adjacent — noted, out of scope for Phase 2.)

### A1. Auto-fire sweep (cost leaks)

Rule being enforced: **no LLM call without an explicit user action.** Pattern sought: `useEffect(() => { …call /explain|/generate|/analyze… }, [])` (mount, empty deps).

| Page | File:line | Endpoint | Verdict |
|---|---|---|---|
| Small Claims Explainer | `SmallClaimsExplainer.tsx:304-307` (calls `startStream` @ `:256`) | `POST /api/small-claims/explain` | ⚠️ **COST LEAK** (confirmed) |
| Criminal Procedure Explainer | `CriminalProcedureExplainer.tsx:361-364` (calls `startStream` @ `:313`) | `POST /api/criminal/explain` | ⚠️ **COST LEAK** (NEW — same defect class as Small Claims) |
| Forms Finder | `FormsFinderFL.tsx:405-407` | `GET /api/forms/facets` | OK (DB read, not LLM) |
| Results | `ResultsPage.jsx:41, 84` | `GET /document/{id}` | OK (DB read) |
| Filing Packet | `FilingPacket.tsx:81-83` | `GET /api/packet/{id}` | OK (DB read; paywall) |
| Paywall | `PaywallPage.jsx` `useEffect` | checkout init | OK (no LLM; paywall) |

**Net new finding:** the Small Claims defect is not isolated. **Criminal Procedure shares the identical triple defect** (HOLLOW + auto-fire + hardcoded key). Both must be fixed together. Discovery, P&C, Wills, Police Report, Expungement, Landlord, Traffic, Case Law, Upload — **no mount auto-fire** (LLM fires only on explicit submit).

### A2. API-key sweep (security)

Hardcoded fallback `"testkey123"` shipped to the client bundle in **7 files**:

| File:line | Notes |
|---|---|
| `src/api.js:11` | **Central axios wrapper** — every call that goes through `api.js` falls back to this key |
| `pages/SmallClaimsExplainer.tsx:260` | gates paid `/api/small-claims/explain` |
| `pages/CriminalProcedureExplainer.tsx:317` | gates paid `/api/criminal/explain` |
| `pages/UploadFlow.jsx:42, 55, 80` | gates `/upload` + `/process` |
| `pages/FormsFinderFL.tsx:20, 431` | gates `/api/forms/*` |
| `pages/ResultsPage.jsx:12, 16, 48, 69, 558, 644` | gates `/document`, `/process`, chat |
| `pages/PaywallPage.jsx:5, 22` | gates `/subscribe` checkout (paywall) |

**Two distinct problems, both real:**
1. **The `|| "testkey123"` fallback** — if `VITE_API_KEY` is unset at build time, the literal ships. This is the publicly-scriptable exposure the user flagged for Small Claims; it is in fact repo-wide.
2. **Client-side `X-API-Key` at all** — even when `VITE_API_KEY` *is* set, the key is embedded in the JS bundle and is therefore public by definition. Any browser user (or script) can extract it and hit gated, paid LLM endpoints directly. This is an architectural exposure, not just a fallback bug.

This is documented as **SECURITY** and prioritized above feature work in Phase 2.

---

## PHASE 2 — INTEGRATION PLAN (document only; nothing implemented)

### Guiding principle
Copy the **P&C pattern** for every surfaced module: an input surface (textarea/form/upload) → an explicit submit action → a streamed result → a UPL disclaimer on every render. No module should fire an LLM call on mount or read its only inputs from the URL.

### P2.0 — MANDATORY fixes (do these FIRST, before any feature surfacing)

#### P2.0.a — SECURITY: remove the hardcoded client API key (priority over features)
**Problem:** 7 files ship `"testkey123"`; the `X-API-Key` model itself is client-side and therefore public.
**Fix path (documented; not implemented here):**
1. **Stop embedding the key in the client.** The `X-API-Key` header is a shared static secret; any value shipped to the browser is public. Options, in order of preference:
   - **Per-origin check on the backend** (recommended): drop client-side `X-API-Key` entirely for user-facing endpoints; in `routes.py` / routers, enforce a strict `Origin`/`Referer` allowlist (the deployed frontend origin) plus the existing CORS config (currently `allow_origins=["*"]` — tighten to the real origins). This binds access to "calls from our frontend," not "calls bearing a known string."
   - **Rate limit** the paid LLM endpoints (`/api/*/explain`, `/api/*/analyze`, `/api/*/generate`) per IP / per session at the backend (e.g. FastAPI middleware or a reverse-proxy limiter). This bounds cost exposure regardless of key leakage.
   - **Session/token auth**: issue a short-lived token from a cheap non-LLM endpoint on first page load; require it for paid endpoints. More work, stronger.
2. **Remove every `|| "testkey123"` fallback** in the 7 files listed in A2; the client should send **no** static key once the server-side guard is in place.
3. **Rotate** whatever the current production `API_KEY` is (it has been in the bundle).
4. **Tighten CORS** in `routes.py:26-31` from `allow_origins=["*"]` to the actual frontend origin(s).
**Files:** `backend/src/api/routes.py`, every file in A2, plus backend rate-limit/origin middleware (new).
**Acceptance (live):** in a browser DevTools session on https://legalclear.app, confirm no `X-API-Key: testkey123` (or any static key) is sent; confirm a `curl` from an off-origin/unknown origin to `/api/small-claims/explain` is **rejected or rate-limited**, not billed.

#### P2.0.b — Small Claims: replace auto-fire with static defaults + explicit submit (user-mandated)
**Problem:** defects (a) + (b) above.
**Fix:**
1. Remove the mount `useEffect` at `SmallClaimsExplainer.tsx:304-307` entirely.
2. Render **static, deterministic default content** on first paint (hardcoded educational copy about FL small claims up to $8,000, where to file, what to bring) — **no API call on mount.**
3. Add an input form mirroring P&C: a situation textarea (minimum), with optional structured fields (claim amount, county). Populate from URL params when present (intake hand-off still works) **but also let the user edit/enter them.**
4. Fire `POST /api/small-claims/explain` **only** on explicit submit (`handleSubmit`), streaming the result into the existing stream panel.
5. Keep the UPL disclaimer on every render.
**Files:** `frontend/src/pages/SmallClaimsExplainer.tsx`. Backend unchanged.
**Acceptance (live):** open https://legalclear.app/small-claims directly (no query params) → page shows static content, **no network call to `/api/small-claims/explain`** in DevTools. Type a situation and click submit → streamed explanation appears with disclaimer.

#### P2.0.c — Criminal Procedure: same fix as Small Claims (mandatory, NEW finding)
**Problem:** `CriminalProcedureExplainer` has the identical triple defect (HOLLOW + auto-fire + hardcoded key).
**Fix:** mirror P2.0.b exactly — remove `CriminalProcedureExplainer.tsx:361-364` mount effect; render static stage-by-stage educational copy on first paint; add an input form (charge type / severity / current stage selectors + free-text) that pre-fills from URL params but is user-editable; fire `/api/criminal/explain` only on submit.
**Files:** `frontend/src/pages/CriminalProcedureExplainer.tsx`. Backend unchanged.
**Acceptance (live):** open https://legalclear.app/criminal-procedure directly → static content, **no mount call** to `/api/criminal/explain`. Select stage + submit → streamed explanation with disclaimer.

#### P2.0.d — Kill the auto-fire pattern repo-wide (rule, not a one-off)
Rule: **no LLM call without explicit user action. Ever.** After P2.0.b/.c, re-run the Phase-1 auto-fire sweep (A1). Any remaining `useEffect(…, [])` that hits an `/explain|/generate|/analyze` endpoint must be converted to a submit handler with static default content on first paint. (Current sweep shows only Small Claims + Criminal are offenders; the rule is codified to prevent regression.)
**Acceptance:** the A1 sweep returns zero LLM auto-fires after these changes.

### P2.1 — Re-surface the 5 orphaned features (the "I don't see my features" problem)

**Root cause of the orphaning:** `HomeHub.tsx:30-38` (`MODULE_TILES`) was rebuilt for the v3 AI-intake hub and contains only **7 tiles** (Small Claims, Criminal, Police Report, Discovery, P&C, Wills & Trusts, Forms). Five built features — **Upload, Expungement, Landlord, Traffic, Case Law** — have live routes and working input UIs but **no inbound link from any reachable page**. The old v1 chrome that linked them (`Navbar.jsx`, `LandingPage.jsx`, `AnalysisDashboard.jsx`, `ExpungementPage.jsx`) is **dead code** (not rendered; App uses `SiteHeader`).

Each is the **smallest viable move**: add a HomeHub tile + (where needed) confirm the page has an input surface. None of these pages auto-fire or need the P&C rewrite — they already have input UIs; they are simply unreachable.

| Phase | Features | Scope | Files touched | Acceptance (live, human in browser) |
|---|---|---|---|---|
| **P2.1.a** | **Upload & Triage (CORE)** + **Case Law** | Add 2 HomeHub tiles. Upload is the platform's core v1 feature (upload court doc → classify → deadline engine → explain → results); it is currently unreachable from home. Case Law is a finished search page. | `frontend/src/pages/HomeHub.tsx` (extend `MODULE_TILES`) | On https://legalclear.app, both tiles render on the home grid; clicking each lands on `/upload` and `/case-law` respectively; Upload's file picker + Case Law's search box both work; deadline result renders on `/results/:id` after upload. |
| **P2.1.b** | **Expungement** + **Traffic** | Add 2 HomeHub tiles. Both pages have working input UIs (eligibility quiz; 3-path traffic wizard). | `frontend/src/pages/HomeHub.tsx` | Tiles render; `/expungement` quiz runs eligibility check on submit; `/traffic` wizard advances through steps and produces a packet link. No mount LLM call on either page. |
| **P2.1.c** | **Landlord / Tenant** + dead-code cleanup | Add 1 HomeHub tile (Landlord has 3 sub-flows already). Delete the 5 dead components (AnalysisDashboard, LandingPage, ExpungementPage, PhaseStub, layout/Navbar) and the dead top-level `/eligibility` route after confirming no live importer — removes confusion about what is surfaced. | `frontend/src/pages/HomeHub.tsx`; delete `pages/AnalysisDashboard.jsx`, `pages/LandingPage.jsx`, `pages/ExpungementPage.jsx`, `pages/PhaseStub.tsx`, `components/layout/Navbar.jsx`; optionally retire `/eligibility` in `routes.py`. | Landlord tile → `/landlord` landing → each of the 3 sub-flows (deposit/repairs/eviction) generates a packet link. `npm run build` passes with the deletions; no route 404s. |

**Ordering rationale:** P2.1.a first because Upload is the core product and the most valuable to re-surface; Case Law rides along (trivial). P2.1.b next (two more wizards). P2.1.c last and bundles the dead-code removal so the nav set and the codebase agree on what exists.

### P2.2 — HEADLESS decisions (document; mostly intentional)

| Feature | Decision | Reason |
|---|---|---|
| Law reference (`/api/law/*`) | **Keep HEADLESS** | Internal — consumed by deadline engine (court closures) + case law. No user-facing page intended. |
| Reminders (`/api/reminders/process`) | **Keep HEADLESS** | Server-side pg_cron job. Correct by design. |
| Triage router (`/api/triage/*`) | **AMBIGUOUS — decide:** retire or wire up. | 0 frontend consumers; `/upload` classifies inline in `routes.py`. Either delete the router or make it the single classification path. Not blocking. |
| Analysis router (`/api/analyze/*`) | **AMBIGUOUS — decide:** retire or wire up. | 0 consumers. Appears to be dead/legacy. |
| Top-level `/eligibility` | **Delete** | DARK — superseded by `/api/expungement/eligibility`; 0 consumers. |

### UPL guardrails (non-negotiable, every newly surfaced module)

Every module surfaced or rewritten in P2.0/P2.1 must, per `core/upl.py` invariants:
1. Carry the disclaimer (legal information ≠ legal advice) on every render, EN and ES.
2. Escalate to attorney referral for high-stakes situations (criminal charges, restraining orders, fatal-severity deadlines with confidence < 0.90) instead of answering — Criminal Procedure in particular must route through the escalation tier check.
3. Never compute a deadline date in the LLM (deadline engine invariant) — the re-surfaced Upload flow already respects this; do not add date arithmetic to any explainer.

### Out of scope (audited only)

- **Filing Packet** (Stripe $35) — SURFACED, paywall.
- **Paywall / Checkout** (`/pay`, `/subscribe`, `/webhook`) — paywall.
- **Chat Expert** (`ChatDrawer`, `/api/chat/{module}`) — paywall (5 free msgs). Note: its `/upgrade` link (`ChatDrawer.tsx:624`) points to an unrouted page — flagged for the paywall track, not fixed here.

---

## Summary

- **SURFACED & correct:** P&C, Wills & Trusts, Police Report, Discovery, Forms, Intake, plus sub-pages (Small Claims Filing Wizard, Results, Filing Packet, Paywall, Chat drawer).
- **HOLLOW + cost leak + security (fix first):** Small Claims Explainer, **Criminal Procedure** (new finding — same defect class).
- **ORPHANED from the hub (the user's "missing features"):** Upload (core!), Expungement, Landlord, Traffic, Case Law — all have working input UIs, just no nav link.
- **SECURITY (top priority):** hardcoded `"testkey123"` in 7 files + client-side `X-API-Key` model + `allow_origins=["*"]` CORS.
- **HEADLESS (intentional):** Law reference, Reminders. **AMBIGUOUS:** Triage router, Analysis router. **DARK:** top-level `/eligibility`, 5 dead frontend components.
