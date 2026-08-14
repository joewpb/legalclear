# S1-x Auth Sweep — Full Route Inventory

Investigation only. No code changed. Repo pinned at `0c2e006` (confirmed via `git log -1`
and `git status --short`, which shows only the two untracked audit files).

Scope covers every route registered in `backend/src/api/routes.py` and every router under
`backend/src/api/routers/`. Auth mechanism verified by reading each route's `dependencies=`
list (or absence thereof) — there are exactly two guard functions in this codebase:
`verify_api_key` (`routes.py:144`) and `require_api_key` (`src/api/dependencies.py:8`).
Both compare `x_api_key` header against `settings.API_KEY`, which defaults to the literal
`"testkey123"` (`src/core/config.py:29`) — this default is S1-1, tracked separately.
Rate limiting verified via `@limiter.limit(...)` decorator presence, backed by
`src/api/limiter.py` (slowapi, keyed by remote address).

## 1. Full route table

| Route | Method | File:line | Auth | Rate limit | LLM | Data touched |
|---|---|---|---|---|---|---|
| `/health` | GET | routes.py:161 | none | none | no | none |
| `/eligibility` | POST | routes.py:165 | **none** | none | yes — `expungement.check_eligibility` (agent) | none (stateless) |
| `/webhook` | POST | routes.py:172 | Stripe signature (`stripe_client.verify_webhook`) — not X-API-Key | none | no | `sessions`, `users`, `packets` (payment status writes) |
| `/api/documents/{document_id}` | DELETE | routes.py:227 | `verify_api_key` | none | no | `documents` — scoped to `session_id` (positive control) |
| `/user` | POST | routes.py:239 | `verify_api_key` | none | no | `users` (create) |
| `/user/{user_id}` | GET | routes.py:243 | `verify_api_key` | none | no | `users` — **no ownership check (IDOR)** |
| `/user/{user_id}/push-token` | POST | routes.py:247 | `verify_api_key` | none | no | `users` push token — **no ownership check (IDOR)** |
| `/subscribe/{user_id}` | POST | routes.py:251 | `verify_api_key` | none | no | Stripe checkout session for arbitrary `user_id` — **no ownership check (IDOR)** |
| `/upload` | POST | routes.py:257 | `verify_api_key` | none | no (classifier runs in `/process`, not here — actually `classifier.classify` IS called here, see below) | `sessions`, `documents` (create) |
| `/process/{session_id}` | POST | routes.py:307 | `verify_api_key` | none | yes — `classifier`, `explainer`, `risk_scanner`, `form_guide`, `expungement` (agents) | `documents`, `sessions` — session ownership not checked against caller |
| `/chat/{document_id}` | POST | routes.py:389 | `verify_api_key` | none | yes — `form_guide.answer_form_question` / `explainer.answer_question` | `documents`, chat history — **no ownership check (IDOR)** |
| `/document/{document_id}` | GET | routes.py:414 | `verify_api_key` | none | no | `documents` — **no ownership check (IDOR)** |
| `/documents/{user_id}` | GET | routes.py:419 | `verify_api_key` | none | no | `documents` for arbitrary `user_id` — **no ownership check (IDOR)** |
| `/florida-filing/prepare` | POST | routes.py:423 | `verify_api_key` | none | no | filing record write, PDF/A generation |
| `/api/analyze/{document_id}` | GET | analysis.py:33 | **none** | none | no (applies UPL guardrails to already-stored text) | `documents` — no ownership check |
| `/api/analyze/stream/{document_id}` | POST | analysis.py:75 | **none** | none | yes — `explainer.explain_stream` | `documents` — no ownership check |
| `/api/attorney-referral/users` | POST | attorney_referral.py:88 | **none** | none | no | `user_profiles` upsert keyed by client-supplied `email` |
| `/api/attorney-referral/users/{user_id}` | GET | attorney_referral.py:128 | **none** | none | no | `user_profiles` — full PII row by UUID |
| `/api/attorney-referral/intake` | POST | attorney_referral.py:138 | **none** | none | yes — Anthropic/DeepSeek direct HTTP call (`_call_ai`) | none persisted here |
| `/api/attorney-referral/submit` | POST | attorney_referral.py:158 | **none** | none | no | `attorney_inquiries` insert |
| `/api/case-law/search` | POST | case_law.py:229 | **none** | none | no (explicitly no LLM — corpus ILIKE search) | `legal_opinions`, `citation_treatment` (read) |
| `/api/chat/{module}` | POST | chat.py:57 | **none** | none | yes — `ChatExpertAgent.chat` (streaming) | none persisted here |
| `/api/criminal/explain` | POST | criminal.py:48 | **none** | 10/min (`@limiter.limit`) | yes — `CriminalProcedureExplainer.explain_stream` | none persisted |
| `/api/deadline/analyze/{document_id}` | POST | deadline.py:16 | `require_api_key` | none | yes — Stage 1 LLM extraction (`deadline.pipeline`) | `documents`, `trigger_events`, `deadlines` — no ownership check |
| `/api/deadline/{document_id}/deadlines` | GET | deadline.py:43 | **none** | none | no | `deadlines` — no ownership check |
| `/api/deadline/{document_id}/trigger-events` | GET | deadline.py:62 | **none** | none | no | `trigger_events` — no ownership check |
| `/api/discovery/analyze` | POST | discovery.py:16 | **none** | 10/min | yes — `DiscoveryMotionAnalyzer.analyze_stream` | none persisted |
| `/api/expungement/eligibility` | POST | expungement.py:56 | **none** | none | no (deterministic disqualifier-list check) | none persisted |
| `/api/expungement/generate` | POST | expungement.py:106 | **none** | none | no (packet builder; no LLM call in this path) | `packets`, Stripe checkout |
| `/api/forms` | GET | forms.py:57 | **none** | none | no | `court_forms` (read) |
| `/api/forms/case-types` | GET | forms.py:194 | **none** | none | no | static in-memory table |
| `/api/forms/recommend` | GET | forms.py:217 | **none** | none | no | `court_forms` (read) |
| `/api/forms/decision-tree` | GET | forms.py:304 | **none** | none | no | static in-memory table |
| `/api/forms/search` | GET | forms.py:331 | **none** | none | no | `court_forms` (read) |
| `/api/forms/facets` | GET | forms.py:362 | **none** | none | no | `court_forms` (read) |
| `/api/forms/counties` | GET | forms.py:396 | **none** | none | no | `court_forms` (read) |
| `/api/forms/meta/{form_number}` | GET | forms.py:439 | **none** | none | no | `court_forms` (read) |
| `/api/forms/suggest` | POST | forms.py:503 | **none** | none | yes — Anthropic `claude-sonnet-4-6` streaming | `court_forms` (read for candidates) |
| `/api/forms/{form_number}` | GET | forms.py:579 | **none** | none | no | `court_forms` + Supabase Storage PDF download |
| `/api/forms/check-updates` | POST | forms.py:643 | `require_api_key` | none | no | `court_forms` write + outbound HEAD/GET to flcourts.gov |
| `/api/intake` | POST | intake.py:127 | **none** | none | yes — Anthropic `claude-haiku-4-5-20251001` | none persisted |
| `/api/landlord/deposit/generate` | POST | landlord.py:86 | **none** | none | no | `packets`, Stripe checkout |
| `/api/landlord/repairs/generate` | POST | landlord.py:91 | **none** | none | no | `packets`, Stripe checkout |
| `/api/landlord/eviction/generate` | POST | landlord.py:96 | **none** | none | no | `packets`, Stripe checkout |
| `/api/law/statutes` | GET | law.py:40 | **none** | none | no | `statutes` (read) |
| `/api/law/rules` | GET | law.py:74 | **none** | none | no | `court_rules` (read) |
| `/api/law/administrative-orders` | GET | law.py:108 | **none** | none | no | `local_administrative_orders` (read) |
| `/api/law/closures` | GET | law.py:125 | **none** | none | no | `court_closures` (read) |
| `/api/packet/build` | POST | packet.py:110 | **none** | none | no | `packets` write, Stripe checkout |
| `/api/packet/walkthrough` | GET | packet.py:117 | **none** | none | no | static JSON |
| `/api/packet/{packet_id}/download` | GET | packet.py:126 | **none** | none | no | packet ZIP file — gated on `status == "paid"`, not on caller identity |
| `/api/packet/{packet_id}` | GET | packet.py:143 | **none** | none | no | packet metadata (incl. `tile_data`, likely PII from intake forms) — no ownership check |
| `/api/packet/{packet_id}/track` | POST | packet.py:151 | **none** | none | no | packet filing-confirmation write |
| `/api/packet/{packet_id}/mark_paid` | POST | packet.py:163 | **none** | none | no | flips packet to `status=paid` — unauthenticated payment bypass |
| `/api/police-report/analyze` | POST | police_report.py:35 | **none** | 10/min | yes — `PoliceReportAnalyzerV2.analyze_stream` | none persisted |
| `/api/police-report/analyze/batch` | POST | police_report.py:70 | **none** | 10/min | yes — `scanner.scan_documents`, `extract_case_context` | none persisted |
| `/api/property-casualty/explain` | POST | property_casualty.py:19 | **none** | 10/min | yes — `PropertyCasualtyExplainer.explain_stream` | none persisted |
| `/api/reminders/process` | POST | reminders.py:29 | `require_api_key` | none | no | `deadlines`, `deadline_reminders` (cron job) |
| `/api/small-claims/generate` | POST | small_claims.py:59 | **none** | 10/min | no (packet builder) | `packets`, Stripe checkout |
| `/api/small-claims/explain` | POST | small_claims.py:92 | **none** | 10/min | yes — `SmallClaimsExplainer.explain_stream` | none persisted |
| `/api/traffic/generate` | POST | traffic.py:37 | **none** | none | no | `packets`, Stripe checkout |
| `/api/triage/classify/{document_id}` | POST | triage.py:16 | `require_api_key` | none | yes — `triage.classify.classify_document` | `documents` write — no ownership check |
| `/api/triage/confirm/{document_id}` | POST | triage.py:92 | `require_api_key` | none | no | `documents` write — no ownership check |
| `/api/wills-trusts/explain` | POST | wills_trusts.py:51 | **none** | 10/min | yes — `WillsTrustsExplainer.explain` | none persisted |

**Total registered app routes: 63** (excluding the conditionally-mounted `compliance` router,
whose contents live outside this repo tree and were not read per scope).
**Unauthenticated routes (no `Depends(verify_api_key)` / `Depends(require_api_key)`, excluding
`/health` and `/webhook` which use a different mechanism): 47.**

This is more than double DECISIONS.md's "~20" estimate. That number likely referred only to
the routes named in AUDIT_FINDINGS §4.9's table, not a full enumeration — the point of this
task. Flagging the gap rather than silently reconciling it.

## 2. Classification of every no-auth route

Per the task's instruction, a route is only marked **"intentional public"** if a comment or
doc in the repo *explicitly* says the endpoint is meant to be public / unauthenticated by
design. I grepped the backend tree for phrasing like "no auth", "public endpoint",
"intentionally public", "no API key" — the only hit was an unrelated comment in
`tests/test_phase_21.py:8` about a missing *Anthropic* key, not about API auth.

**No route in this codebase carries an explicit "this is intentionally public" statement.**
Several routers have comments describing *what kind of data* they serve (e.g. "read-only
lookups against verbatim official text" in `law.py:1-6`), which is suggestive but not a
statement about the auth boundary — the docstring is about content provenance (never
fabricate case-law URLs, etc.), not about who may call the endpoint. So every group below is
formally **UNVERIFIED-INTENT**; the sub-grouping is my read of *how plausible* public-by-design
is per the content shape, so Joe can triage fast, not a verified fact.

### A. Reference data — plausible public-by-design, but UNVERIFIED-INTENT (no explicit statement found)
Official, non-personal, statewide legal reference text/forms with no user-specific data in
the response.

- `GET /api/law/statutes` (law.py:40), `/rules` (:74), `/administrative-orders` (:108),
  `/closures` (:125) — verbatim FL statutes/rules/AOs/closures. `law.py:1-6` docstring: "All
  endpoints are read-only lookups against verbatim official text." Describes content, not auth.
- `GET /api/forms` (forms.py:57), `/case-types` (:194), `/decision-tree` (:304), `/search`
  (:331), `/facets` (:362), `/counties` (:396), `/meta/{form_number}` (:439),
  `/{form_number}` download (:579) — official FL court forms and their catalog metadata.
  `forms.py:1-6` docstring says forms are "served... through the LegalClear domain" so the
  court's servers aren't hit — again a content/architecture statement, not an auth-intent one.
- `POST /api/case-law/search` (case_law.py:229) — FL appellate opinion corpus search, no LLM,
  no PII.
- `GET /api/packet/walkthrough` (packet.py:117) — static walkthrough JSON, no user data.

### B. LLM cost exposure — unauthenticated, no rate limit at all
The audit's biggest concern: anyone can run these to burn Anthropic/DeepSeek spend, no key,
no throttle.

- `POST /eligibility` (routes.py:165) — expungement agent
- `POST /api/analyze/stream/{document_id}` (analysis.py:75) — explainer agent (also IDOR, see §3)
- `POST /api/attorney-referral/intake` (attorney_referral.py:138) — Anthropic/DeepSeek direct call
- `POST /api/chat/{module}` (chat.py:57) — ChatExpertAgent, streaming
- `POST /api/forms/suggest` (forms.py:503) — Claude sonnet streaming
- `POST /api/intake` (intake.py:127) — Claude haiku classifier

### C. LLM cost exposure — unauthenticated but rate-limited (10/min per IP)
Same cost-exposure shape as B, but at least throttled per-source-IP (bypassable via IP
rotation, but not zero-cost to an attacker).

- `POST /api/criminal/explain` (criminal.py:48)
- `POST /api/discovery/analyze` (discovery.py:16)
- `POST /api/police-report/analyze` (police_report.py:35)
- `POST /api/police-report/analyze/batch` (police_report.py:70)
- `POST /api/property-casualty/explain` (property_casualty.py:19)
- `POST /api/small-claims/explain` (small_claims.py:92)
- `POST /api/wills-trusts/explain` (wills_trusts.py:51)

### D. PII or tenancy exposure — unauthenticated
No LLM cost angle; the risk is reading/writing another person's data.

- `POST /api/attorney-referral/users` (attorney_referral.py:88) — upsert by client-supplied
  email; no auth means anyone can overwrite any profile row by supplying that email.
- `GET /api/attorney-referral/users/{user_id}` (attorney_referral.py:128) — full profile
  (email, phone, case summary) by UUID guess, no auth.
- `POST /api/attorney-referral/submit` (attorney_referral.py:158) — writes an inquiry tied to
  an arbitrary `user_id`; no auth, no ownership check on that `user_id`.
- `GET /api/deadline/{document_id}/deadlines` (deadline.py:43) — any `document_id` → that
  user's computed legal deadlines, no auth at all.
- `GET /api/deadline/{document_id}/trigger-events` (deadline.py:62) — same, for extracted
  trigger events.
- `GET /api/analyze/{document_id}` (analysis.py:33) — classification + analysis text for any
  `document_id`, no auth.
- `GET /api/packet/{packet_id}` (packet.py:143) — packet metadata including `tile_data`
  (the intake form contents — names, addresses, defendant info, etc. depending on packet
  type), no auth, no ownership check.
- `GET /api/packet/{packet_id}/download` (packet.py:126) — the actual filing ZIP, gated only
  on `status == paid`, not on who is asking.

### E. Payment-related — unauthenticated
- `POST /api/packet/{packet_id}/mark_paid` (packet.py:163) — flips a packet to paid with no
  auth and no payment verification. Router docstring at packet.py:164-169 calls this
  "Dev-only convenience... Safe to call multiple times — idempotent," acknowledging it's a
  workaround, not a claim that public access is intended. Currently low-severity because
  `PAYMENTS_ENABLED` defaults false (packets are marked paid automatically in that mode per
  `build_packet_with_checkout`, packet.py:44-67) — moot while payments are off, live risk the
  moment payments flip on.

### F. Other / packet-generation write endpoints — unauthenticated, no LLM, no rate limit
Write endpoints that build a filing packet (PDF generation + optional Stripe checkout) with
no auth and no throttle. Cost exposure here is compute (PDF/A generation), not LLM tokens, and
each also writes a `packets` row and can create a live Stripe checkout session.

- `POST /api/expungement/eligibility` (expungement.py:56) — deterministic, no packet write
- `POST /api/expungement/generate` (expungement.py:106)
- `POST /api/landlord/deposit/generate` (landlord.py:86)
- `POST /api/landlord/repairs/generate` (landlord.py:91)
- `POST /api/landlord/eviction/generate` (landlord.py:96)
- `POST /api/packet/build` (packet.py:110)
- `POST /api/packet/{packet_id}/track` (packet.py:151)
- `POST /api/traffic/generate` (traffic.py:37) — audit explicitly names this file:line as a
  no-rate-limit gap
- `POST /api/small-claims/generate` (small_claims.py:59) — this one IS rate-limited (10/min),
  unlike its siblings above; noted here for parity with the others' function, not for the
  rate-limit gap.

## 3. Key-gated-but-no-ownership-check routes (IDOR) — note only, not fixed here

These require a valid `X-API-Key` (or would, once S1-1 removes the insecure default) but
never verify the caller owns the resource keyed by the path parameter — any key holder can
read/act on any other user's data:

- `GET /user/{user_id}` — routes.py:243
- `POST /user/{user_id}/push-token` — routes.py:247
- `POST /subscribe/{user_id}` — routes.py:251 (creates a Stripe checkout scoped to an
  arbitrary user_id — lower severity than read/write PII, but still cross-tenant)
- `POST /process/{session_id}` — routes.py:307 (session ownership not checked against caller)
- `POST /chat/{document_id}` — routes.py:389 (AUDIT_FINDINGS §4.9 names this explicitly)
- `GET /document/{document_id}` — routes.py:414 (named in §4.9)
- `GET /documents/{user_id}` — routes.py:419 (named in §4.9)
- `POST /api/deadline/analyze/{document_id}` — deadline.py:16
- `POST /api/triage/classify/{document_id}` — triage.py:16
- `POST /api/triage/confirm/{document_id}` — triage.py:92

Positive control confirming the pattern exists elsewhere and simply wasn't applied to the
above: `DELETE /api/documents/{document_id}` (routes.py:227-238) checks `session_id` against
the document before deleting.

## 4. Frontend call-site check

Checked `frontend/src/api.js` (the shared axios client — only used by `FormsFinderFL.tsx` for
`GET /api/forms/search`) plus a repo-wide grep for `fetch(`/`api.get(`/`api.post(` across
`frontend/src/pages` and `frontend/src/components`.

**Called by the shipped frontend** (confirms these are live user-facing surfaces, not dead code):
`/api/packet/{id}/mark_paid`, `/api/packet/{id}`, `/api/packet/{id}/download`,
`/api/case-law/search`, `/api/intake`, `/api/deadline/{id}/deadlines`, `/document/{id}`,
`/api/deadline/analyze/{id}`, `/florida-filing/prepare`, `/chat/{id}`,
`/api/criminal/explain`, `/api/expungement/eligibility`, `/api/forms/search`,
`/api/forms/suggest`, `/api/attorney-referral/intake`, `/api/attorney-referral/submit`,
`/api/police-report/analyze`, `/api/property-casualty/explain`, `/upload`,
`/process/{id}`, `/api/discovery/analyze`, `/eligibility`, `/api/small-claims/explain`,
`/api/landlord/eviction/generate`, `/api/chat/{module}` (ChatDrawer.tsx),
`/api/landlord/deposit/generate`, `/api/landlord/repairs/generate`,
`/api/expungement/generate`, `/api/traffic/generate`, `/api/packet/walkthrough`,
`/api/small-claims/generate`, `/api/packet/{packet_id}/track` (FilingTracker.tsx:57).
`WillsTrustsExplainer.tsx` and `PaywallPage.jsx` also call
their respective endpoints (`/api/wills-trusts/explain`, a `/checkout/{documentId}` route not
found in the backend — likely stale/dead frontend call, **UNVERIFIED**, out of scope to chase
further here) but weren't captured verbatim by the grep pattern; spot-read confirms the calls
exist.

**No frontend call site found** for (uncalled routes — backend-only, cron, admin, or dead code):
- `/user`, `/user/{user_id}`, `/user/{user_id}/push-token`, `/subscribe/{user_id}` — no
  matches for `/user`, `/subscribe`, or `push-token` anywhere under `frontend/src`.
- `GET /documents/{user_id}` — no match.
- `GET /api/analyze/{document_id}`, `POST /api/analyze/stream/{document_id}` — no match
  (this analysis.py router appears to be superseded by the deadline/triage/process flow that
  the frontend actually drives).
- `GET /api/attorney-referral/users/{user_id}`, `POST /api/attorney-referral/users` — no
  match (the frontend only calls `/intake` and `/submit` on that router).
- `POST /api/deadline/analyze` is called, but `GET .../deadlines` and `.../trigger-events` —
  `.../deadlines` IS called (ResultsPage.jsx:15); `.../trigger-events` has **no frontend
  call site found**.
- `POST /api/forms/check-updates`, `POST /api/triage/classify`, `POST /api/triage/confirm`,
  `POST /api/reminders/process` — all key-gated ops endpoints (cron/admin), no frontend match
  expected or found.
- `GET /api/forms` (bare list), `/case-types`, `/decision-tree`, `/facets`, `/counties`,
  `/recommend`, `/meta/{form_number}` — no match found for these specific forms sub-routes
  beyond `/api/forms/search` and `/api/forms/suggest`; **UNVERIFIED** whether another page
  calls them under a path this grep pattern missed (e.g. via a helper function rather than an
  inline `fetch`) — flagging rather than asserting dead code.
- (resolved below) `POST /api/packet/{packet_id}/track` — direct read of
  `packet/FilingTracker.tsx:57` confirms it calls this exact endpoint
  (`/api/packet/${packetId}/track?confirmation_number=...`) — **is called**, move to the
  called list in the paragraph above.

## 5. What's verified vs inferred vs open

**Verified by direct read:** every route's decorator/`dependencies=` line, the two auth guard
function bodies, the rate limiter wiring, and which agent/LLM call (if any) each handler makes.
Frontend call sites verified by grep + the specific files quoted above.

**Inferred, not verified:**
- The "plausible public-by-design" grouping in §2A is my judgment call from content shape
  (official, non-personal, statewide text), not a confirmed intent — treat as UNVERIFIED-INTENT
  per the task's own rule, not as cleared.
- `PoliceReportAnalyzerV2`, `DiscoveryMotionAnalyzer`, etc. internals were not opened; "LLM:
  yes" is inferred from `analyze_stream` naming + the SSE/streaming pattern consistent with
  every other confirmed-LLM router in this codebase, not from reading each agent file line by
  line.

**Open / unresolved:**
- `PaywallPage.jsx:23` calls `${API_URL}/checkout/{documentId}` — grepped the entire backend
  for `checkout` (8 files matched: config.py, routes.py, stripe_client.py, packet.py,
  small_claims.py, traffic.py, expungement.py, landlord.py) and none of them register a route
  at that path — the only checkout-related routes are `/subscribe/{user_id}` (routes.py:251)
  and the packet-builder's internal `_create_checkout` (packet.py:70). **This frontend call
  target does not exist in the backend** — either dead/stale frontend code from a prior
  paywall design, or PaywallPage.jsx itself is unreachable/unused in the current router tree.
  Not fixed here (out of scope — investigation only) but worth flagging since it's a broken
  call path, not a security gap.
- Whether any `/api/forms/*` sub-routes beyond `/search` and `/suggest` are called through a
  shared helper rather than an inline fetch call (would make them live even without a direct
  grep hit).
- The exact discrepancy between DECISIONS.md's "~20" estimate and the 47 counted here — not
  resolved, just surfaced. Recommend Joe re-read AUDIT_FINDINGS §4.9 against this table before
  scoping the S1-x fix session, since the fix surface is roughly double what was estimated.
