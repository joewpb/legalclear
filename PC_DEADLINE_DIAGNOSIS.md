# P&C Deadline Tool — Diagnosis (rev. 2026-07-04)

**Scope:** read-only, non-destructive. No code changed, no prod services started.
**P&C = Property & Casualty** — Module 5 of the v3 explainer set.

> This revision supersedes the prior "WORKING / no deadline tool exists" verdict.
> That verdict was wrong: the P&C agent **does** compute deadlines and emit
> `key_deadlines` for first-party property. The real failure mode is below.

---

## VERDICT

**HIDDEN** — the P&C deadline tool exists end-to-end and is fully wired, but the
"Key Deadlines" card section never renders in any normal product flow because
**the UI never captures `date_of_loss`**, the single trigger input the
deterministic deadline engine needs to compute anything.

A secondary **ERRORING** defect (a `NameError` inside `_compute_deadlines`) was
also present and is fixed in code on `origin/main` (commit `cdf8e46`, 2026-07-04)
— but even with that fix the cards still won't show without a `date_of_loss`
input path, so the HIDDEN condition is the binding root cause.

---

## EVIDENCE — every check

### A. Frontend — exists and mounted?  → exists, mounted, NOT flag-gated

| # | Check | Result | Evidence |
|---|---|---|---|
| A1 | Component located | **PASS** | `frontend/src/pages/PropertyCasualtyExplainer.tsx` (493 lines) |
| A2 | Router mount | **PASS** | `frontend/src/App.tsx:71` — `<Route path="/property-casualty" element={<PropertyCasualtyExplainer />} />` (no lazy/flag gate) |
| A3 | Nav/menu entry | **PASS** | `frontend/src/pages/HomeHub.tsx:35` — tile `{ title: "Property & Casualty", subtitle: "Insurance and liability", to: "/property-casualty", icon: "🏠" }`; deep-link builder `:55` |
| A4 | Flag/env gate | **PASS (none)** | No feature-flag or env conditional around the route or tile; render is unconditional |
| A5 | Error boundary | **PASS (none swallowing)** | No `ErrorBoundary`/`errorElement` in `frontend/src/`; a throw would crash loudly, not hide the section |
| A6 | Build/typecheck | **NA** | Not re-run this session; route imports cleanly and prior `tsc --noEmit` was exit 0 |

### B. Backend — endpoint exists and answers?  → exists, registered, imports, computes

| # | Check | Result | Evidence |
|---|---|---|---|
| B7 | Route registration | **PASS** | `backend/src/api/routes.py:57` import, `:76` `app.include_router(property_casualty_router)`; router prefix `/api/property-casualty`, endpoint `POST /explain` (`routers/property_casualty.py:19`) |
| B8 | Import + compute | **PASS** | `uv run python` smoke: imports OK; `_compute_deadlines(date(2026,7,4))` returned **5 deadlines** — report-claim 2027-07-04 (§627.70132), supplemental 2028-01-04, file-suit 2031-07-04 (§95.11(2)(e)), insurer pay-or-deny 2026-09-02 (§627.70131), pre-suit NOI 2026-07-17 (§627.70152) |
| B9 | Live smoke | **PASS (route live)** | `curl …/openapi.json` on prod `zesty-delight-production-b533.up.railway.app` lists `/api/property-casualty/explain`, `/api/deadline/analyze/{document_id}`; root `/` → 404 (no root handler, expected) |
| B10 | CORS | **PASS (permissive)** | `routes.py:26-28` — `allow_origins=["*"]`; no origin/Tailscale IP restriction to trip on |

### C. Data — rules source present?  → hardcoded dict, all P&C keys present

| # | Check | Result | Evidence |
|---|---|---|---|
| C11 | Rules source | **PASS (hardcoded)** | Rules are a hardcoded `RULES` dict in `backend/deadline/rules.py:34` (**not** a DB table; `RULES_VERSION = "2026-05-19-v1"`). All 5 P&C keys present: `pc_report_claim` (:159), `pc_supplemental_claim` (:176), `pc_file_suit` (:193), `pc_pay_or_deny` (:215), `pc_notice_of_intent` (:236). Smoke confirmed 0 missing. |

### D. Integration — does FE call BE?  → yes, correctly

| # | Check | Result | Evidence |
|---|---|---|---|
| D12 | FE → BE call | **PASS** | `PropertyCasualtyExplainer.tsx:283` reads `VITE_API_URL \|\| "http://localhost:8001"`; `:291` `fetch(\`${base}/api/property-casualty/explain\`, …)`. `frontend/.env.production` → prod Railway host. Correct host, correct path. |

---

## ROOT CAUSE — why the deadline cards never appear

The "Key Deadlines" cards render under a compound guard
(`PropertyCasualtyExplainer.tsx:380`):

```tsx
{isFirstParty && resp.key_deadlines && resp.key_deadlines.length > 0 && ( … )}
```

`resp.key_deadlines` is populated **only** when the backend computes deadlines,
and the backend computes **only** when it can parse `date_of_loss` from
`entities` (`backend/src/agents/property_casualty.py:328-331`):

```python
if is_first_party:
    loss_date = self._parse_date_of_loss(entities)
    if loss_date:
        computed_deadlines = self._compute_deadlines(loss_date)
```

**The page has no UI to enter `date_of_loss`.** `entities` is built exclusively
from URL query params (`PropertyCasualtyExplainer.tsx:263-264`):

```js
const entities = {};
sp.forEach((v, k) => { if (!["sub_type","language"].includes(k)) entities[k] = v; });
```

The only `<input>` on the entire page is a **file upload**
(`PropertyCasualtyExplainer.tsx:339`, `type="file"`). There is no
`<input type="date">`, no text field, and nothing appended to the FormData as
`date_of_loss`. Consequence chain:

- `entities.date_of_loss` is always `undefined` in normal use
- `_parse_date_of_loss()` returns `None` (`property_casualty.py:202`)
- `computed_deadlines` stays `None`
- `parsed["key_deadlines"]` is never assigned (`:378`, `:449`)
- the render guard at `:380` is always false → **"Key Deadlines" never shows**

The tool is reachable only if an operator hand-crafts a URL like
`/property-casualty?sub_type=first_party_property&date_of_loss=2026-07-04`,
which no normal user does.

### Secondary defect — fixed in code, deploy unverified

Before commit `cdf8e46` (2026-07-04, "fix: NameError in `_compute_deadlines`
(rule → RULES[rule_key])"), `_compute_deadlines` referenced an undefined name
`rule`, so even a valid `date_of_loss` would have raised `NameError` mid-stream
and broken the explain response. The fix is present locally and on `origin/main`
(HEAD == origin/main, 0 ahead / 0 behind). Whether Railway `zesty-delight` has
redeployed `cdf8e46` was not verified from this harness; regardless, the
HIDDEN condition above blocks the feature with or without this fix.

---

## FIX TIER

**targeted** — one small, additive UI change unblocks the feature. No
architectural work, no new endpoints, no DB changes. The backend is correct.

## NEXT ACTION (single, minimal)

Add a **date-of-loss date picker** to `PropertyCasualtyExplainer.tsx`
(first-party branch only) that writes its value into the `entities` object
under the key `date_of_loss`. It is then already serialized into
`entities_json` at `:286` with no further wiring. The picker should emit ISO
`YYYY-MM-DD`, which `_parse_date_of_loss` already accepts
(`property_casualty.py:202-207`). Flow then closes:
`isFirstParty && date_of_loss` → backend computes → `key_deadlines` populates →
cards render.

Optional hardening: when first-party is selected but no date of loss is
provided, show a hint ("Enter your date of loss to see your statutory
deadlines") so the absence is explained to the user.

---

## NOT FIXING (per mandate)

No code changed. No services started. This file is the only artifact.
