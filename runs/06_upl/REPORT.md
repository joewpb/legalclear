# UPL Wall Gap Diagnosis — S1-6 / S3-2 (Group A item 6)

**Run:** 06_upl — investigation only, no code changed. Repo at `main` (audit baseline 0c2e006).
**Defect under diagnosis:** AUDIT_FINDINGS.md:301 (triage row S3-2); DECISIONS.md:76 (Group A item 6).

---

## 1. What the UPL wall actually is (`backend/src/core/upl.py`)

**VERIFIED by reading the whole file.**

- `apply_disclaimer(output: dict, lang="en", level="standard") -> dict` — `upl.py:95-105`. Pure function: shallow-merges three keys onto any output dict: `disclaimer` (canonical text from `_DISCLAIMERS`, `upl.py:31-74`, levels `standard`/`urgent`/`criminal`, EN+ES), `attorney_referral_links` (`upl.py:76-92`), and `language`. It does **not** stream, hook, or intercept anything — it only works if a call site remembers to invoke it.
- Escalation path: `check_escalation(...)` at `upl.py:134-229` returns an `EscalationResult` (`upl.py:114-131`) with `should_escalate`, `disclaimer_level`, referral links, and referral text. Triggers (`upl.py:161-217`): criminal/expungement → level `criminal`, unknown doc type, minor children, fatal deadline with confidence < 0.90 (`FATAL_CONFIDENCE_THRESHOLD`, `upl.py:110`), deadline within 72h (`URGENT_HOURS`, `upl.py:111`).
- Nudge layer: `nudge_for_attorney` / `apply_upl_guardrails` (`upl.py:295-327`) append attorney nudges when directive phrases appear — advisory, not blocking.
- **Key architectural fact:** there is no middleware or router-level enforcement. Each router/agent opts in individually. That is the mechanism of the gap: the wall is a library, not a wall.

There is a **second, parallel disclaimer source**: `core/disclaimer.py` — `get_disclaimer(language)` returning plain strings (`DISCLAIMER_EN` at `disclaimer.py:11-18`, ES at `:20-26`). Criminal and Discovery use this one; PC uses `upl.apply_disclaimer`. Two canonical texts exist side by side (verified: `criminal_procedure.py:16`, `discovery_motion.py:21`, `wills_trusts.py:16` import `core.disclaimer`; `property_casualty.py:31` imports `core.upl`).

---

## 2. Where the disclaimer sits today, per surface

### 2a. `agents/criminal_procedure.py` (streaming: `explain_stream`, :132-220)

**VERIFIED.**

- **SUCCESS path** (`:150-200`): raw LLM text chunks are yielded as `data: {chunk}\n\n` (`:163-165`); after the stream, the accumulated text is parsed and a single-line typed event `{"type": "relevant_opinions", ...}` is yielded (`:195-200`). **No server-side disclaimer event is ever emitted on success.** If JSON parse fails post-stream, the generator just `return`s (`:170-179`) — again no disclaimer.
- **ERROR path** (`:208-220`): the catch-all yields `{"error": true, "message": ..., "disclaimer": get_disclaimer(language)}` (`:213-220`). So **only failures carry a server disclaimer**.
- **LLM-emitted disclaimer:** the SYSTEM_PROMPT's JSON schema ends with `"disclaimer: string }"` (`criminal_procedure.py:50`). On success the disclaimer exists only if the model chooses to populate that field — a prompt-level request, not an enforcement.
- Non-streaming `explain()` **is** enforced server-side: `parsed["disclaimer"] = get_disclaimer(language)` at `:251` and error dict at `:262`. The gap is streaming-only.
- Router `api/routers/criminal.py:53-70` is a pure pass-through (`StreamingResponse` around `explain_stream`); no disclaimer added there. Endpoint is rate-limited, no auth (`criminal.py:48-50`).

### 2b. `agents/discovery_motion.py` (streaming: `analyze_stream`, :132-214)

**VERIFIED.** Structurally identical gap.

- **SUCCESS path** (`:173-210`): raw chunks yielded (`:181-183`); post-stream a deterministic `{"type": "risk_analysis", ...}` event is yielded (`:206-208`). **No disclaimer event on success.** Parse failure post-stream → silent `pass` (`:209-210`).
- **ERROR paths** all carry `disclaimer: get_disclaimer(language)`: PDF extraction failure `:159`, empty text `:163`, unsupported type `:170`, stream exception `:214`.
- **LLM-emitted disclaimer:** SYSTEM_PROMPT schema includes `"disclaimer: string }"` at `discovery_motion.py:78` — same prompt-only reliance.
- Non-streaming `analyze()` enforces server-side at `:257` and on errors (`:233,236,238,282`).
- Router `api/routers/discovery.py:28-35`: pass-through `StreamingResponse`, no disclaimer.

### 2c. `api/routers/attorney_referral.py` (whole file, :1-253)

**VERIFIED — the router has no UPL import of any kind.** Imports (`:12-24`) are httpx/fastapi/pydantic/settings/DatabaseManager only; grep for `apply_disclaimer`, `get_disclaimer`, `upl` in the file returns nothing.

Responses carrying legal-ish guidance, none wrapped:

- `POST /intake` (`:138-155`): returns `IntakeResponse` with raw LLM `content` from `_call_ai` (`:185-244`, Claude Haiku with DeepSeek fallback). The system prompt (`:67-83`) says "NEVER give legal advice" and includes urgency routing ("court <72h, eviction, arrest → tag URGENT, tell them to call 800-342-8011") — i.e., the model actively discusses the user's criminal/eviction situation, exactly the escalation tier `check_escalation` labels `criminal`/`immediate`, with zero disclaimer and only prompt-level protection.
- `POST /submit` (`:158-180`): returns a fixed message with an expectation ("An attorney will review it within 1-2 business days", `:179`) — low risk, but still outside the wall.
- The hard-fallback string (`:239-244`) mentions the FL Bar referral line — informational, no disclaimer.
- `/users` endpoints (`:88-135`): profile CRUD, no legal content — genuinely no disclaimer needed.
- Client side: `pages/AttorneyReferralFL.tsx` contains **no** disclaimer text at all (grep for `disclaimer|legal advice|legal information` → zero hits). So no layer — server or client — puts a disclaimer on the intake chat. **VERIFIED.**

### 2d. Canonical controls

- **wills_trusts pattern** (`agents/wills_trusts.py:166,182-185`): computes `disclaimer = get_disclaimer(language)` up front (`:166`), then after the text stream **the server yields a dedicated terminal event** `data: {"disclaimer": ...}` (`:183`) followed by `data: {"done": true}` (`:185`). Error path also carries it (`:195`). Note wills_trusts wraps every chunk as `{"chunk": ...}` JSON (`:180`), so its client can trivially discriminate — its stream is typed throughout, unlike criminal/discovery which stream raw JSON text.
- **property_casualty pattern** (`agents/property_casualty.py:378-380`): after streaming raw chunks, the server re-parses the full text and **re-emits the entire payload wrapped by the real UPL wall**: `final = apply_disclaimer(parsed, lang=language)` (`:379`) then `yield f"data: {json.dumps(final)}\n\n"` (`:380`). Error paths also use `apply_disclaimer` (`:337,341,344,386`). Docstring states the invariant explicitly: "Disclaimer: ALWAYS injected via src.core.upl.apply_disclaimer()" (`property_casualty.py:10`). This is the only streaming module using `core.upl` rather than `core.disclaimer`.

---

## 3. Client streaming contract

### CriminalProcedureExplainer (`frontend/src/pages/CriminalProcedureExplainer.tsx`) — VERIFIED

- `readSSE` (`:55-72`) splits on `\n` and yields the payload of every `data: ` line.
- Parse loop (`:397-419`): for each chunk it first tries `JSON.parse(chunk)`; if it parses **and** `solo.type === "relevant_opinions"` it consumes it as a typed event and `continue`s (`:403-408`); otherwise the chunk is appended to `full` and the accumulator is re-parsed (`:411-418`). Final parse at `:421-425`.
- **Tolerance of a new server event:** a new single-line typed event such as `{"type": "disclaimer", ...}` would parse as complete JSON but **fail the `relevant_opinions` check, fall through, and be appended to `full`** — corrupting the accumulated explanation JSON so the final `JSON.parse(full)` at `:422` throws → "Could not parse the explanation." So the criminal client does **not** tolerate arbitrary typed events; it whitelists exactly one. (Caveat: if the extra event arrives *after* `full` already parsed successfully once at `:416`, the UI state may survive, but the final-parse error at `:424` would still set an error banner — either way it breaks. Exact UX consequence is inferred, not executed.)
- An event shaped `{"disclaimer": "..."}` **without** a `type` field (the wills_trusts shape) would likewise be appended to `full` and corrupt it. Any server-side event addition requires a client whitelist change.
- Disclaimer rendering today: `:488-491` renders `response.disclaimer` (the LLM-JSON field) **with a hard-coded client fallback string** — this fallback is the only reason users currently see any disclaimer when the LLM omits the field.

### DiscoveryMotionAnalyzer (`frontend/src/pages/DiscoveryMotionAnalyzer.tsx`) — VERIFIED

- Same structure, compressed: SSE line splitter at `:78-81`; per-chunk whitelist of exactly `type === "risk_analysis"` at `:174`; everything else accumulates into `full` at `:175`; final parse at `:177` (preserving `risk_analysis` across the merge). Same fragility: any new typed event lands in `full` and breaks the final parse. Client fallback disclaimer at `:237` (`resp.disclaimer || "LegalClear provides legal information..."`).

### The tolerant reference: `components/policereport/sseMerge.ts` — VERIFIED

- Pure, unit-tested reducer (`sseMerge.test.ts` exists alongside). `applySseEvent` (`sseMerge.ts:56-89`) is a discriminated-union switch over typed events (`risk_analysis`, `relevant_opinions`, `case_context`, `analysis_json`) with order-independent carry-over semantics (`:82-85`): a typed event set earlier survives a later `analysis_json` merge that omits the field. The header comment (`:1-16`) documents the exact backend emission contract. This is the pattern the audit means by "police-report pattern shows how": adding a `disclaimer` typed event there would be one new union member + one switch case, with tests.

---

## 4. Minimal fix footprint (described, not written)

**Backend — Criminal** (`agents/criminal_procedure.py`):
- Insert one server-side terminal event on the success path. The natural landing point is immediately after the `async with ... stream` block closes, i.e. between `:165` and the post-stream parse at `:167` (or after the opinions block at `:200`, before falling out of the `try`). Emitting **before** the opinions/parse logic is safer — it then also covers the parse-failure `return` at `:179`. Shape choice: either the wills_trusts one-liner `yield data: {"disclaimer": get_disclaimer(language)}` or, better for client discrimination, a *typed* event `{"type": "disclaimer", "disclaimer": ...}`. Level: this surface is criminal — the `apply_disclaimer`/`_DISCLAIMERS["criminal"]` text (`upl.py:59-73`) is arguably the right copy, which argues for `apply_disclaimer({}, lang, level="criminal")` rather than `get_disclaimer`.
- No router change needed (`routers/criminal.py:53-60` passes chunks through).

**Backend — Discovery** (`agents/discovery_motion.py`):
- Same insertion between `:183` (end of chunk loop) and `:185` (risk-score block), or as a typed event yielded alongside/after the `risk_analysis` event at `:208` — but before-the-parse placement also covers the silent `pass` at `:209-210`.

**Backend — Attorney referral** (`routers/attorney_referral.py`):
- `POST /intake` (`:150-155`): wrap the response — since it returns a Pydantic `IntakeResponse` (`:43-47`), the minimal change is either (a) add `disclaimer` + `attorney_referral_links` fields to the model and populate from `apply_disclaimer`, or (b) return `apply_disclaimer({...}, lang)` as a plain dict. Language is a wrinkle: `IntakeRequest` (`:38-40`) carries **no `language` field**, so a true `apply_disclaimer(lang=...)` wrap needs a request-model addition (violating the "every user-facing string accepts a language parameter" constraint is the current state).
- `POST /submit` (`:176-180`): wrap the returned dict in `apply_disclaimer` — one-line.
- Add the `from ...core.upl import apply_disclaimer` import near `:23`.

**Frontend — Criminal** (`pages/CriminalProcedureExplainer.tsx`):
- The per-chunk whitelist at `:403-408` must accept the new event: one more branch (`solo.type === "disclaimer"` → `setResponse(p => ({...p, disclaimer: solo.disclaimer})); continue;`). If instead the untyped wills_trusts shape (`{"disclaimer": ...}`) is chosen, the check would be `"disclaimer" in solo && Object.keys(solo).length small` — messier; the typed shape is strictly easier here. Rendering at `:488-491` already reads `response.disclaimer`, so no render change.

**Frontend — Discovery** (`pages/DiscoveryMotionAnalyzer.tsx`):
- Same one-branch addition at `:174`; rendering at `:237` already reads `resp.disclaimer`.

**Frontend — Attorney referral** (`pages/AttorneyReferralFL.tsx`):
- Currently renders no disclaimer at all; would need a display element for the new response field (exact insertion point not mapped — see UNVERIFIED).

**Deploy coupling:** the backend event must not ship before the client whitelist change is live on `appealing-victory`, or every criminal/discovery streaming success will hit the corrupted-accumulator failure described in §3. Ship client tolerance first (it's a no-op against the current backend), then the backend event.

---

## 5. Verified vs. inferred vs. UNVERIFIED

**Verified (read the code at the cited lines):** everything in §1, §2, §3 above; both agents' system prompts requesting an LLM `disclaimer` field (`criminal_procedure.py:50`, `discovery_motion.py:78`); non-streaming paths being server-enforced; routers being pass-throughs; attorney_referral having zero UPL imports server-side and zero disclaimer text client-side; sseMerge's order-independent typed-event semantics.

**Inferred (consistent with code, not executed):** the exact runtime failure mode of an unrecognized event on the criminal/discovery clients (accumulator corruption → final-parse error banner) — reasoned from `:398-425` / `:174-177`, not reproduced against a live stream; that the LLM does sometimes omit the `disclaimer` JSON field (the client fallback strings at `CriminalProcedureExplainer.tsx:489-490` and `DiscoveryMotionAnalyzer.tsx:237` strongly suggest the authors observed this, but I have no transcript evidence).

**UNVERIFIED / open questions for the fix run:**
- Whether any test currently pins the criminal/discovery SSE emission contract (I did not sweep `backend/tests/` for stream-shape tests; `sseMerge.test.ts` covers only the police-report reducer).
- Which disclaimer source the fix should standardize on — `core.disclaimer.get_disclaimer` (wills_trusts, and the error paths of both gapped agents) vs `core.upl.apply_disclaimer` (PC, and what the audit's proposed fix names). The audit says "wrap referral responses in `apply_disclaimer`" but cites both `:183` (get_disclaimer pattern) and `:379` (apply_disclaimer pattern) as acceptable models; a decision is needed, ideally converging the two texts.
- Whether the ES-language wrinkle on `/intake` (no `language` in `IntakeRequest`, `attorney_referral.py:38-40`) is in scope for the minimal fix.
- Exact placement for a disclaimer element in `AttorneyReferralFL.tsx` (component internals not read beyond the disclaimer grep).
