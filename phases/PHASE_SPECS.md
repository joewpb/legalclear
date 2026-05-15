# LegalClear — Phase Specs (REBUILT)

Supersedes the prior `phases/PHASE_SPECS.md`. The earlier version's Part A
naming was a reconstruction and was **wrong from Phase 2 onward** — the
phase-orchestrator caught this on its first reconcile pass against the oneshot.
This file corrects it.

## Provenance — read before trusting anything here

| Section | Source | Confidence |
|---|---|---|
| Part A names + goals (0–14) | The verbatim oneshot prompt | **Canonical.** Confirmed by Claude Code's reconcile. |
| Part A verify commands + pass criteria | NOT transcribed here on purpose | Lift verbatim from the oneshot — Claude Code has it in hand. Do not reconstruct. |
| Part B goals / verify / pass (15–23) | `LegalClear_Complete_Phases_0-23.md`, "AI legal app clarification" chat, 2026-05-12 | **Solid.** Cross-confirmed across retrievals. |
| Part B per-phase deliverables + code | Same doc — NOT retrievable through search | **MISSING.** Splice from your copy. Marked `<<< VERBATIM SOURCE >>>` below. |

Hard rule: do not execute any Part B phase until its `<<< VERBATIM SOURCE >>>`
marker is resolved from the May 12 document.

---

# PART A — phases 0-14 — VERIFY ONLY

Corrected mapping. The orchestrator runs each verify command, confirms what
exists, and **never rebuilds**. Verify commands + pass criteria are in the
oneshot — Claude Code lifts them from there, not from this file.

| # | Phase | Status | Note |
|---|---|---|---|
| 0 | Scaffold | DEPLOYED — re-verify | — |
| 1 | Document ingestion | DEPLOYED — re-verify | `/api/upload` lives here. Never touch it. |
| 2 | Core utilities | DEPLOYED — re-verify | Was mislabeled "Classifier agent" in old ledger. |
| 3 | Classifier agent | DEPLOYED — re-verify | — |
| 4 | Explainer agent | DEPLOYED — re-verify | — |
| 5 | Form guide agent | DEPLOYED — re-verify | — |
| 6 | Risk scanner agent | DEPLOYED — re-verify | — |
| 7 | Expungement agent | DEPLOYED — re-verify | `expungement.py` belongs here — not "unaccounted for". |
| 8 | Memory layer | DEPLOYED — re-verify | — |
| 9 | Payments | DEPLOYED — re-verify | Old ledger's "Phase 9 = Mobile" was wrong. Real Phase 9 = Payments, passes. |
| 10 | API | DEPLOYED — re-verify | — |
| 11 | Florida courts | DEPLOYED — re-verify | `florida_courts.py` present, Mode A form — consistent with current no-Mode-B policy. Re-verify against oneshot deliverables. |
| 12 | Web frontend | DEPLOYED — re-verify | — |
| 13 | Mobile app | **OUT-OF-SCOPE (v1)** | `mobile/` is empty. Decision: not a v1 blocker. Do not build, do not count as a fail. Revisit post-v1. |
| 14 | Deploy | DEPLOYED — divergence noted | Oneshot specced systemd; repo + AGENTS.md use Railway. Railway is canonical (hardened policy supersedes oneshot — same precedent as the Mode B rule). Mark DEPLOYED with this note. |

### Port note (from the oneshot header)
Port `8000` is reserved for the **Nemotron inference container** — it is not
off-limits in general. AGENTS.md's "8000 = build failure" rule is specifically
about binding *the app* to 8000. Both statements are consistent. The app stays
on `8001`.

### Mode B note (from the oneshot footer)
The oneshot references Florida Mode B env vars
(`FLORIDA_PORTAL_EMAIL` / `FLORIDA_PORTAL_PASSWORD`). Mode B was part of the
original Part A Florida design. AGENTS.md's current "no Mode B automation in
`backend/src/`" is a **hardened policy that supersedes the oneshot**. The repo's
`florida_courts.py` is the Mode A version — consistent with current policy.
Leave it Mode A.

---

# PART B — phases 15-23 — BUILD TARGET

Goal / verify / pass are solid. The `<<< VERBATIM SOURCE >>>` line in each phase
is where the deliverables + code from `LegalClear_Complete_Phases_0-23.md` must
be pasted before that phase executes.

### Phase 15 — Hub + Small Claims tile
- **Goal:** app hub loads; a Small Claims tile routes into the wizard.
- **verify:** hub route renders; Small Claims tile present and navigates.
- **pass:** hub renders without error; tile click lands on the wizard route.
- `<<< VERBATIM SOURCE: Phase 15 deliverables + code — splice from May 12 doc >>>`

### Phase 16 — Small Claims 5-step wizard
- **Goal:** a 5-step guided wizard collecting Small Claims filing inputs.
- **verify:** all 5 steps render and advance; state persists across steps.
- **pass:** wizard completes start to finish; collected state survives step nav.
- `<<< VERBATIM SOURCE: Phase 16 deliverables + code — splice from May 12 doc >>>`

### Phase 17 — i18n (en/es) + review screen
- **Goal:** language layer with `en` and `es`; review screen honors selected language.
- **verify:** review screen renders with `en` selected and with `es` selected.
- **pass:** both language paths render the review screen correctly.
- `<<< VERBATIM SOURCE: Phase 17 deliverables + code — splice from May 12 doc >>>`

### Phase 18 — Filing Packet generation
- **Goal:** Generate produces the Filing Packet — 3 PDFs bundled into one ZIP.
- **verify:** Generate yields a ZIP; ZIP contains exactly 3 PDFs.
- **pass:** ZIP downloads; unzips to exactly 3 valid PDFs.
- `<<< VERBATIM SOURCE: Phase 18 deliverables + code — splice from May 12 doc >>>`

### Phase 19 — Stripe Filing Packet payment
- **Goal:** "LegalClear Filing Packet" Stripe product at $35.00; pay flow;
  `?paid=1` redirect; download gated behind payment.
- **verify:** test card `4242 4242 4242 4242` completes; redirect to `?paid=1`;
  ZIP download available only after payment.
- **pass:** unpaid users cannot download; paid users land on `?paid=1` and can.
- `<<< VERBATIM SOURCE: Phase 19 deliverables + code — splice from May 12 doc >>>`

### Phase 20 — Florida courts walkthrough
- **Goal:** filing walkthrough for myflcourtaccess.com — 8+ steps. Builds on the
  existing `florida_courts.py` (Mode A). **No Mode B automation.**
- **verify:** walkthrough renders 8+ steps; `grep` confirms no Mode B automation
  in `backend/src/`.
- **pass:** 8+ steps render; grep for Mode B automation in `backend/src/` is clean.
- `<<< VERBATIM SOURCE: Phase 20 deliverables + code — splice from May 12 doc >>>`

### Phase 21 — Tracking page
- **Goal:** user enters a court confirmation number; tracking page reflects status.
- **verify:** entering a test confirmation number updates the tracking page.
- **pass:** test confirmation number produces a visible status update.
- `<<< VERBATIM SOURCE: Phase 21 deliverables + code — splice from May 12 doc >>>`

### Phase 22 — Integration wire-up + polish
- **Goal:** end-to-end wiring across hub → wizard → packet → pay → walkthrough → tracking.
- **verify:** full happy-path runs start to finish without manual intervention.
- **pass:** the complete v1 flow runs unbroken, no manual steps.
- `<<< VERBATIM SOURCE: Phase 22 deliverables + code — splice from May 12 doc >>>`

### Phase 23 — Full v1 verification + deploy
- **Goal:** all Part B phase tests pass; deploy to Railway; emit final report.
- **verify:** `test_phase_15.py` … `test_phase_23.py` and `test_full_v1.py` all pass.
- **pass:** every Part B test green; both Railway services deployed; report emitted.
- `<<< VERBATIM SOURCE: Phase 23 deliverables + code — splice from May 12 doc >>>`

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
Part A verified: Phases 0-14 (existing, deployed; Phase 13 Mobile out-of-scope v1)
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
