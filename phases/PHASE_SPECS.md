# LegalClear — Phase Specs

Goal, verification command, and pass criteria per phase. **Part A** entries are
verify-only — the orchestrator runs the command, never rebuilds. **Part B**
entries are full build specs.

Verification commands below are **starting points** — tighten them against the
real repo layout on first run. Commands assume repo root as working directory
and the backend running on `:8001`, frontend on `:3000`.

---

# PART A — phases 0-14 — VERIFY ONLY

### Phase 0 — Project scaffold
- **Goal:** FastAPI backend, React frontend, React Native shell, Supabase
  project, Stripe account wired.
- **verify:** `test -d backend && test -d frontend && test -f backend/pyproject.toml && grep -q "8001" backend/**/*.py`
- **pass:** backend + frontend dirs exist; `uv` project file present; backend bound to 8001.

### Phase 1 — Document ingestion
- **Goal:** PDF parser (PyMuPDF), OCR pipeline (Tesseract), raw-text handler,
  file storage in Supabase.
- **verify:** `grep -rIl "fitz\|PyMuPDF" backend/src && grep -rIl "tesseract\|pytesseract" backend/src && curl -s -o /dev/null -w "%{http_code}" localhost:8001/api/upload`
- **pass:** parser + OCR refs present; `/api/upload` responds. **Do not modify `/api/upload`.**

### Phase 2 — Classifier agent
- **Goal:** detects document type, jurisdiction, extracts key metadata.
- **verify:** `grep -rIl "classif" backend/src/agents`
- **pass:** classifier agent module exists and returns a typed dict.

### Phase 3 — Explainer agent
- **Goal:** plain-language summary + Q&A chat loop, disclaimer baked into the
  system prompt.
- **verify:** `grep -rIl "explain" backend/src/agents && grep -rIi "disclaimer\|not legal advice" backend/src/agents`
- **pass:** explainer module exists; disclaimer present in its system prompt.

### Phase 4 — Form guide agent
- **Goal:** field-by-field walkthrough, jurisdiction-aware filing instructions.
- **verify:** `grep -rIl "form" backend/src/agents`
- **pass:** form guide module exists and returns a typed dict.

### Phase 5 — Risk scanner agent
- **Goal:** clause scoring (red/yellow/green), red-flag detection.
- **verify:** `grep -rIl "risk" backend/src/agents && grep -rIi "red\|yellow\|green" backend/src/agents`
- **pass:** risk scanner module exists; three-tier scoring present.

### Phase 6 — Output layer
- **Goal:** structured report generation, PDF export of results.
- **verify:** `grep -rIl "report\|pdf" backend/src`
- **pass:** report builder + PDF export path exist.

### Phase 7 — Payments
- **Goal:** Stripe pay-per-use, token gate, usage tracking in Supabase.
- **verify:** `grep -rIl "stripe" backend/src`
- **pass:** Stripe integration + usage-tracking table reference exist.

### Phase 8 — Web frontend
- **Goal:** upload flow, results dashboard, Q&A interface, payment wall.
- **verify:** `test -d frontend/src && curl -s -o /dev/null -w "%{http_code}" localhost:3000`
- **pass:** frontend builds and serves; upload + results + payment views present.

### Phase 9 — Mobile
- **Goal:** React Native camera scan, OCR pipeline, shares backend logic.
- **verify:** `grep -rIl "react-native" . --include=package.json`
- **pass:** RN project exists; camera + OCR path present.

### Phases 10-14 — STUB — reconstruct from repo
- **Goal:** unknown. Not in hand.
- **Orchestrator action:** inspect the deployed repo, determine what 10-14
  actually built, write the real goal + verify command + pass criteria here,
  and propose for confirmation before marking anything verified. Do not execute
  past an unresolved stub.

---

# PART B — phases 15-23 — BUILD TARGET

Scope reconstructed from the v1 deployment smoke test. **Confirm each phase
against the verbatim source build prompt before executing.** Each phase needs:
goal, deliverables, verification command, pass criteria. Fill the
`<<< SOURCE >>>` blocks from the original prompt.

### Phase 15 — Hub + Small Claims tile
- **Goal:** app hub loads; a Small Claims tile routes into the wizard.
- **verify:** hub route renders; Small Claims tile present and navigates.
- `<<< SOURCE: paste verbatim Phase 15 spec — deliverables, test, pass criteria >>>`

### Phase 16 — Small Claims 5-step wizard
- **Goal:** a 5-step guided wizard collecting Small Claims filing inputs.
- **verify:** all 5 steps render and advance; state persists across steps.
- `<<< SOURCE: paste verbatim Phase 16 spec >>>`

### Phase 17 — i18n (en/es) + review screen
- **Goal:** language layer with `en` and `es`; review screen honors selected language.
- **verify:** review screen renders with `en` selected and with `es` selected.
- `<<< SOURCE: paste verbatim Phase 17 spec >>>`

### Phase 18 — Filing Packet generation
- **Goal:** Generate produces the Filing Packet — 3 PDFs bundled into one ZIP.
- **verify:** Generate yields a ZIP; ZIP contains exactly 3 PDFs.
- `<<< SOURCE: paste verbatim Phase 18 spec >>>`

### Phase 19 — Stripe Filing Packet payment
- **Goal:** "LegalClear Filing Packet" Stripe product at $35.00; pay flow;
  `?paid=1` redirect; download gated behind payment.
- **verify:** test card `4242 4242 4242 4242` completes; redirect to `?paid=1`;
  ZIP download available only after payment.
- `<<< SOURCE: paste verbatim Phase 19 spec >>>`

### Phase 20 — Florida courts walkthrough
- **Goal:** filing walkthrough for myflcourtaccess.com — 8+ steps. Builds on the
  existing `florida_courts.py` (Mode A); **no Mode B automation**.
- **verify:** walkthrough renders 8+ steps; `grep` confirms no Mode B automation
  in `backend/src/`.
- `<<< SOURCE: paste verbatim Phase 20 spec >>>`

### Phase 21 — Tracking page
- **Goal:** user enters a court confirmation number; tracking page reflects status.
- **verify:** entering a test confirmation number updates the tracking page.
- `<<< SOURCE: paste verbatim Phase 21 spec >>>`

### Phase 22 — Integration wire-up + polish
- **Goal:** end-to-end wiring across hub → wizard → packet → pay → walkthrough → tracking.
- **verify:** full happy-path runs start to finish without manual intervention.
- `<<< SOURCE: paste verbatim Phase 22 spec >>>`

### Phase 23 — Full v1 verification + deploy
- **Goal:** all Part B phase tests pass; deploy to Railway; emit final report.
- **verify:** `test_phase_15.py` … `test_phase_23.py` and `test_full_v1.py` all pass.
- `<<< SOURCE: paste verbatim Phase 23 spec >>>`

---

# Deployment (after Phase 23 passes)

1. **Backend:** `uv sync` → commit → push to GitHub `main` → Railway auto-deploys `zesty-delight`.
2. **Frontend:** `npm run build` → commit → push to GitHub `main` → Railway auto-deploys `appealing-victory`.
3. **Stripe dashboard:** confirm "LegalClear Filing Packet" product at $35.00 is visible.
4. **Smoke test:**
   - Hub loads → Small Claims tile → 5-step wizard → review with `en` selected → Generate.
   - Land on Filing Packet page → pay $35 with test card `4242 4242 4242 4242`.
   - Redirect to `?paid=1` → download ZIP → confirm 3 PDFs inside.
   - View Walkthrough → see 8+ steps for myflcourtaccess.com.
   - Enter test confirmation number → tracking page updates.

---

# Final report format

After all Part B phases (15-23) deploy successfully, the orchestrator outputs
**exactly** this and nothing outside it:

```
=== LEGALCLEAR V1 FULL DEPLOYMENT REPORT ===
Part A verified: Phases 0-14 (existing, deployed)
Part B completed: Phases 15, 16, 17, 18, 19, 20, 21, 22, 23
Frontend bundle hash: [hash]
Backend deploy: success
Frontend deploy: success
Live URLs:
  Frontend: [url]
  Backend: [url]
Stripe product configured: yes ($35 Filing Packet)
Languages live: en, es
Verification:
  test_phase_15.py: passed
  test_phase_16.py: passed
  test_phase_17.py: passed
  test_phase_18.py: passed
  test_phase_19.py: passed
  test_phase_20.py: passed
  test_phase_21.py: passed
  test_phase_22.py: passed
  test_phase_23.py: passed
  test_full_v1.py: passed
TODOs remaining: [count of `# TODO:` markers]
Mode B automation present: no
Blocking issues: none
=== END REPORT ===
```

Do not claim success if any assertion failed at any phase. If Mode B automation
is detected anywhere in `backend/src/`, fail the build.
