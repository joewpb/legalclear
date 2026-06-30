# SPEC_LEDGER.md

Canonical mapping of every router/agent in `routes.py` to its governing spec. This is the single lookup future spec prompts diff against before any code is written. Last fully re-verified against source: **2026-06-30**.

Spec-version key: `v1-oneshot` = `archive/Complete One Shot Build.md` / `LegalClear_OneShot_Prompt.md`; `v2-phase` = `phases/source/PHASE_*.md` or `phases/BUILD_PLAN.md`; `v3-undocumented` = exists in code, in no spec document.

---

## 1. LEDGER TABLE

Registration lines are in `backend/src/api/routes.py`.

| Module | Router (file) | Agent (file) | Governing spec | Spec version | Last verified | Drift status | Owner action |
|---|---|---|---|---|---|---|---|
| AI Intake Router | `routers/intake.py` (reg :72) | none — inline Haiku call (`intake.py:122`) | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Small Claims | `routers/small_claims.py` (reg :73) | `agents/small_claims.py` | `PHASE_16_small_claims.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Criminal Procedure | `routers/criminal.py` (reg :74) | `agents/criminal_procedure.py` | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Motion for Discovery | `routers/discovery.py` (reg :75) | `agents/discovery_motion.py` | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Property & Casualty | `routers/property_casualty.py` (reg :76) | `agents/property_casualty.py` | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Expungement | `routers/expungement.py` (reg :77) | `agents/expungement.py` | `PHASE_17_expungement_ui.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Landlord/Tenant | `routers/landlord.py` (reg :78) | `services/packet_builder.py` (shared) | `PHASE_18_landlord_tenant.md` | v2-phase | 2026-06-30 | MINOR | N |
| Traffic | `routers/traffic.py` (reg :79) | `services/packet_builder.py` (shared) | `PHASE_20_traffic.md` | v2-phase | 2026-06-30 | MINOR | N |
| Police Report | `routers/police_report.py` (reg :80) | `agents/police_report_v2.py` + `agents/scanner.py` (parallel) | `PHASE_21_police_report.md` + `BUILD_PLAN` Phase 9 | v2-phase | 2026-06-30 | MAJOR | Y |
| Case Law | `routers/case_law.py` (reg :81) | none — inline Anthropic call (`case_law.py:72`) | `PHASE_22_case_law.md` | v2-phase | 2026-06-30 | MINOR | N |
| Packet Builder | `routers/packet.py` (reg :82) | `services/packet_builder.py` | `PHASE_23_packet_builder.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Forms | `routers/forms.py` (reg :83) | inline `SUGGEST_MODEL` (`forms.py:30`) | `PHASE_19_forms_finder.md` + Phase 2/10 | v2-phase | 2026-06-30 | MINOR | Y |
| Law Corpus | `routers/law.py` (reg :84) | none — verbatim DB lookup | `BUILD_PLAN` Phase 3 | v2-phase | 2026-06-30 | MINOR | Y |
| Deadline Engine | `routers/deadline.py` (reg :85) | `deadline/{extract,compute,pipeline}.py` | `BUILD_PLAN` Phase 4 + `PHASE_10_api.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Triage Classifier | `routers/triage.py` (reg :86) | `triage/classify.py` + `agents/classifier.py` | `BUILD_PLAN` Phase 5 + `PHASE_03_classifier_agent.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Reminders | `routers/reminders.py` (reg :87) | `core/{reminders,notifications}.py` | `BUILD_PLAN` Phase 6 | v2-phase | 2026-06-30 | MAJOR | Y |
| Analysis / UPL | `routers/analysis.py` (reg :88) | `agents/{explainer,form_guide,risk_scanner}.py` | `BUILD_PLAN` Phase 8 + `PHASE_04/05/06_*.md` | v2-phase | 2026-06-30 | MAJOR | Y |
| Chat Expert | `routers/chat.py` (reg :89) | `agents/chat_expert.py` | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Wills & Trusts | `routers/wills_trusts.py` (reg :90) | `agents/wills_trusts.py` | **UNDOCUMENTED — v3** | v3-undocumented | 2026-06-30 | N/A — no spec | Y |
| Compliance (optional) | `_compliance_router` (reg :101, gated) | none | none — feature-gated behind `compliance/` pkg | n/a | 2026-06-30 | NONE | N |

Drift-status basis (MAJOR items): Small Claims = response contract replaced by packet builder + paywall bypassed; Expungement = router ignores its own agent, hardcoded JSON rules, phantom `Phase 07`/`v1.1` TODO; Police Report = `/analyze` silently swapped to streaming, `scan_documents` modified against Phase 9 guardrail, parallel v1/v2 impls; Packet = $35 paywall disabled in code (contradicts CLAUDE.md); Deadline = unhandled `int(circuit)`/`date.fromisoformat`, muted fatal-deadline closure escalation, sync client in async, partial-write 200; Triage = 18-label taxonomy matches no spec, Haiku model drift; Reminders = TOCTOU + no real email delivery; Analysis = streaming-success path emits no disclaimer (U1), IDOR on document lookups, no router auth.

---

## 2. UNDOCUMENTED SURFACE REGISTRY (v3)

| Module | What it does | Spec it should have had | Recommendation |
|---|---|---|---|
| **AI Intake Router** (`routers/intake.py`) | Classifies a free-text user situation into one of 6 modules + extracts entities via Haiku; returns module + entities to the client. | A Phase-10-era "intake/routing" spec defining the module taxonomy, the entity schema, and its relationship to the Phase 3 document classifier. | **(b) Reconcile/rebuild.** Defect, not feature: it bypasses the Phase 3 `ClassifierAgent` entirely (two disconnected classifiers), runs an undocumented Haiku model, feeds nothing downstream, swallows errors to HTTP 200, and is unauthenticated. Do not retroactively spec the bypass — spec must describe routing that reuses the canonical classifier, carries auth, and surfaces failures. |
| **Criminal Procedure** (`routers/criminal.py` + `agents/criminal_procedure.py`) | Streaming plain-language explainer for criminal-procedure documents. | A v3 module spec (parallel to `PHASE_04_explainer_agent.md`) with UPL constraints specific to criminal matter. | **(b) Spec describes correct behavior; code must change.** The module is a legitimate feature, but the spec must mandate third-person framing + disclaimer-on-every-stream, and the code currently emits no disclaimer on the streaming success path (U1). Spec the correct behavior; fix U1 against it. |
| **Motion for Discovery** (`routers/discovery.py` + `agents/discovery_motion.py`) | Streaming analyzer for discovery motions (PDF/image vision input), structured findings + risk score. | A v3 module spec. | **(b) Same as Criminal Procedure** — legitimate feature, but spec must require disclaimer-on-stream + third-person; code has U1 + the `ask_attorney` directive-schema leak + list-of-strings `.get()` crash. |
| **Property & Casualty** (`routers/property_casualty.py` + `agents/property_casualty.py`) | Streaming explainer for property/casualty situations. | A v3 module spec. | **(b) Same** — U1 + `ask_attorney` directive schema. |
| **Wills & Trusts** (`routers/wills_trusts.py` + `agents/wills_trusts.py`) | Streaming explainer for wills/trusts documents. | A v3 module spec. | **(a) Document as intended — with constraints.** This is the one streaming agent that emits a correct `{"done": true}` + disclaimer terminal event. Spec it to match behavior, but bake in auth + the model pin. |
| **Chat Expert** (`routers/chat.py` + `agents/chat_expert.py`) | Multi-module conversational Q&A across 6 legal topics. | A v3 spec (distinct from Phase 10's single-doc `/api/chat`). | **(a) Document as intended — with constraints.** `chat_expert.py` is the codebase's positive-control template (appends disclaimer after stream on both success and error; prompts enforce third-person + no-directives). Spec it to match, bake in auth + Sonnet pin. Do not let the weaker explainer agents inherit by copying them. |

Net: 2 modules are acceptable-to-document (Wills, Chat Expert — they follow the known-good template); 4 are defects-to-reconcile (Intake bypass; Criminal/Discovery/P&C streaming-disclaimer + UPL gaps). No v3 module gets a spec that merely describes its current bugs.

---

## 3. DUPLICATE / PARALLEL IMPLEMENTATION REGISTRY

| Parallel set | Implementations | Canonical going forward | To deprecate | Dead code to remove (once migration verified) |
|---|---|---|---|---|
| Police Report analysis | `agents/police_report_v2.py` (`PoliceReportAnalyzerV2`, async streaming, drives `/analyze`) vs `agents/scanner.py` (`scan_documents` + `extract_case_context`, sync, drives legacy `/analyze/batch`) — both imported at `routers/police_report.py:16–17` | `agents/police_report_v2.py` | `agents/scanner.py` (v1) | After migrating `/analyze/batch` (`police_report.py:67–102`) onto `PoliceReportAnalyzerV2` or removing it: delete `scanner.py:174–246` (`scan_documents`) and the legacy batch route. **Keep** `extract_case_context` (`scanner.py:269–311`) until relocated into `police_report_v2.py` or `case_context.py` — it is live via `/analyze/batch`. |
| Expungement eligibility | `agents/expungement.py` `ExpungementAgent.check_eligibility()` (LLM, used in `routes.py:133,305`) vs `routers/expungement.py:51–98` (hardcoded JSON substring match against `data/fl_disqualifying_offenses.json`) | `agents/expungement.py` (`ExpungementAgent`) | `routers/expungement.py` hardcoded `/eligibility` body | `routers/expungement.py:51–98` + the phantom `# TODO … Phase 07 … v1.1` (`:54`). Wire `/eligibility` to `ExpungementAgent` first. |
| Classification | `agents/classifier.py` (Phase 3 document-type classifier, 18-label) vs `routers/intake.py` inline classifier (situation→module routing) | Both legitimate **if documented as distinct** — document-type vs situation-routing are different jobs | Neither, until a decision | If merged: delete the inline Haiku call in `intake.py:121–205` and route through `ClassifierAgent`. If kept separate: add both to Section 1 with explicit distinct specs. |
| Form catalog (source of truth) | `routers/forms.py` (serves `court_forms` table, 443 published) vs `agents/form_guide.py:38–41` (loads `data/forms_library.json`, ~6 entries, 2026-05-14) | `court_forms` Supabase table (via `forms.py`) | `form_guide.py` JSON loader | `data/forms_library.json` + `form_guide.py:35–43`; rewrite `FormGuideAgent` to read `court_forms` (Phase 10 ingest never reached it). |

---

## 4. MODEL PINNING REGISTRY

CLAUDE.md pins `claude-sonnet-4-6`. Every LLM call-site in the repo:

| File:line | Model | Intended (sonnet-4-6) | Justified deviation | Note |
|---|---|---|---|---|
| `deadline/extract.py:124` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/chat_expert.py:152` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/criminal_procedure.py:79` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/discovery_motion.py:82` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/explainer.py:27` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/expungement.py:42` (`guide_model`) | claude-sonnet-4-6 | ✓ | N | — |
| `agents/expungement.py:43` (`eligibility_model`) | **claude-haiku-4-5-20251001** | ✗ | **N — undocumented** | If Haiku is intentional for cheap eligibility screening, it must be recorded as a documented exception here and in CLAUDE.md. |
| `agents/form_guide.py:32` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/police_report_v2.py:156` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/property_casualty.py:81` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/risk_scanner.py:34` | **claude-haiku-4-5-20251001** | ✗ | **N — undocumented** | Same: document as exception or revert to Sonnet. |
| `agents/scanner.py:137` (`_MODEL`) | claude-sonnet-4-6 | ✓ | N | — |
| `agents/small_claims.py:50` | claude-sonnet-4-6 | ✓ | N | — |
| `agents/wills_trusts.py:106` | claude-sonnet-4-6 | ✓ | N | — |
| `routers/case_law.py:72` | claude-sonnet-4-6 | ✓ | N | — |
| `routers/forms.py:30` (`SUGGEST_MODEL`) | claude-sonnet-4-6 | ✓ | N | — |
| `routers/intake.py:122` (`_MODEL`) | **claude-haiku-4-5-20251001** | ✗ | **N — undocumented** | Intake is undocumented (Section 2); model choice is unresolved pending reconcile. |
| `agents/classifier.py:37` | **claude-haiku-4-5-20251001** | ✗ | **N — undocumented** | Triage classifier — pipeline-critical. Phase 3 verification greps for `claude-sonnet-4-6` and would fail. |

4 undocumented Haiku deviations. Rule: any non-Sonnet call-site requires a `Y` in this column with a stated reason; `N` means the deviation is a defect to resolve.

---

## 5. DEPENDENCY SOURCE-OF-TRUTH DECLARATION

**Production source of truth: `pip` + `backend/requirements.txt`** — not uv.

Evidence: `backend/nixpacks.toml` (the `[phases.install]` comment, verbatim): *"The Nixpacks Python provider detects requirements.txt, creates the /opt/venv virtualenv, puts /opt/venv/bin on PATH, and runs `pip install -r requirements.txt` automatically."* Railway's Nixpacks build installs from `requirements.txt`. `pyproject.toml` exists only to support local `uv` workflows (its own header admits this). The two have already drifted: `httpx` is in `requirements.txt` (load-bearing for `case_law.py`, `forms.py`) but **not** in `pyproject.toml`'s `dependencies`, so `uv sync` produces a broken local env.

**Going-forward rule (single source of truth):**
- `backend/requirements.txt` is canonical for production. Every dependency added or bumped must be added there first.
- `pyproject.toml` is a generated/synced mirror for local `uv` dev only. It MUST be regenerated from `requirements.txt` in the same commit (or the drift returns).
- CLAUDE.md's "uv-ONLY … never pip/venv directly" invariant is **inaccurate for production** and must be corrected to: *"Local dev uses uv against pyproject.toml; production (Railway/Nixpacks) installs from requirements.txt via pip. requirements.txt is canonical — keep pyproject.toml in sync."*
- Alternative (out of scope here, requires a deploy change): migrate Nixpacks to install via `uv sync` from `pyproject.toml`, then delete `requirements.txt` and make pyproject the single source. Pick one; do not keep both authoritative.

---

## 6. CHANGE PROTOCOL

Enforceable checklist. Every future spec prompt follows this before touching the repo.

- [ ] **Locate the module's row** in the Section 1 ledger before writing any code.
- [ ] **If no row exists:** it is a new module. Write the spec FIRST (`phases/source/PHASE_NN_*.md`), add the ledger row (governing spec + version + drift = NONE), THEN build.
- [ ] **If the row is `v3-undocumented`:** do not extend it. Resolve it per Section 2 (write the spec describing correct behavior, or reconcile/rebuild) before adding features on top.
- [ ] **If drift status is MAJOR:** do not build on top of it. Resolve the drift per the Section 2 or Section 3 action first.
- [ ] **Any new LLM call-site:** add a row to Section 4. Non-Sonnet models require a `Y` justification or they are a defect.
- [ ] **Any dependency change:** edit `requirements.txt` first (Section 5), then sync `pyproject.toml` in the same commit.
- [ ] **In the same PR/commit as the code change:** update the affected ledger row's `Last verified` date and `Drift status`. Never after. Never batched.
- [ ] **If a parallel/duplicate implementation is introduced or resolved:** update Section 3 in the same commit.

This ledger is the diff target. A module not traceable to a row here, or a row whose drift is MAJOR and unaddressed, blocks the change.
