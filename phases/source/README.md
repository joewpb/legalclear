# LegalClear — Phased Build Folder

**Drop these phase files into Antigravity one at a time. Each phase is fully self-contained — the agent reads only that phase file and executes only that phase.**

## Stack reminder

Pop OS / Ubuntu · Antigravity IDE · uv · Python 3.11 · FastAPI on `localhost:8001` · React/Vite frontend · Anthropic API (`claude-sonnet-4-6`) · Supabase · Stripe · Playwright · Railway hosting · Florida jurisdiction only.

## Two-part build

| Part | Phases | Status | Per-file action |
|---|---|---|---|
| **A** | 00–14 | ✅ Built & deployed | **VERIFY ONLY** — confirm files/endpoints exist. Do NOT rebuild. |
| **B** | 15–23 | ❌ To build | **EXECUTE** — full build, verify each before next. |

## Phase index

| File | Phase | Title | Action |
|---|---|---|---|
| `PHASE_00_setup.md` | 0 | Project scaffold + venv | Verify |
| `PHASE_01_memory.md` | 1 | DB / memory layer (SQLite → Supabase) | Verify |
| `PHASE_02_pdf_processor.md` | 2 | PDF extraction + OCR pipeline | Verify |
| `PHASE_03_classifier_agent.md` | 3 | Classifier Agent | Verify |
| `PHASE_04_explainer_agent.md` | 4 | Explainer Agent | Verify |
| `PHASE_05_form_guide_agent.md` | 5 | Form Guide Agent | Verify |
| `PHASE_06_risk_scanner_agent.md` | 6 | Risk Scanner Agent | Verify |
| `PHASE_07_expungement_agent.md` | 7 | Expungement Agent | Verify |
| `PHASE_08_supabase.md` | 8 | Supabase production DB | Verify |
| `PHASE_09_payments.md` | 9 | Stripe paywall | Verify |
| `PHASE_10_api.md` | 10 | FastAPI backend consolidation | Verify |
| `PHASE_11_fl_courts_v1.md` | 11 | FL Courts Mode A initial | Verify |
| `PHASE_12_web_frontend.md` | 12 | React + Tailwind frontend | Verify |
| `PHASE_13_mobile_app.md` | 13 | React Native (Expo) | Verify |
| `PHASE_14_deploy.md` | 14 | Railway / nginx deploy | Verify |
| `PHASE_15_hub_restructure.md` | 15 | 8-tile HomeHub + Brutalist CSS | Build |
| `PHASE_16_small_claims.md` | 16 | Small Claims FL wizard | Build |
| `PHASE_17_expungement_ui.md` | 17 | Expungement quiz UI + endpoint | Build |
| `PHASE_18_landlord_tenant.md` | 18 | Landlord/Tenant 3 sub-flows | Build |
| `PHASE_19_forms_finder.md` | 19 | Court Forms Finder (data-driven) | Build |
| `PHASE_20_traffic.md` | 20 | Traffic/Tickets wizard | Build |
| `PHASE_21_police_report.md` | 21 | Police Report Analyzer | Build |
| `PHASE_22_case_law.md` | 22 | FL Case Law Lookup (CourtListener) | Build |
| `PHASE_23_packet_builder.md` | 23 | Mode A Filing Pipeline (PDF/A + EN/ES + $35 Stripe) | Build |

## Workflow per phase

1. Open Antigravity in fresh session.
2. Paste the single phase file into context.
3. Switch to Planning mode → agent outputs its plan → review.
4. Approve → switch to Fast mode → execute.
5. Agent runs `test_phase_N.py` at the end.
6. If all pass: agent prints `PHASE [N] COMPLETE — all checks passed.`
7. If anything fails twice: agent prints `PHASE [N] BLOCKED — [error]` and STOPS.
8. Close session. Open new session for next phase.

**One phase = one session = zero context bleed = zero drift.**

## Universal rules (printed in every phase file)

- **uv only.** No `pip`, no `python3` direct.
- **Backend on 8001.** Nemotron lives on 8000. Never swap.
- **No automation against `myflcourtaccess.com`.** Mode A only. Phase 23 has a hard test that scans every Python file in `backend/src/` for the string `myflcourtaccess` and fails the build if any non-comment match is found.
- **Florida jurisdiction only.** No multi-state in v1.
- **Brutalist design tokens** (defined in Phase 15) mandatory on every new frontend component.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output before `json.loads()`.

## Final integration

After Phase 23 passes, run `test_full_v1.py` (included in Phase 23 file) to verify the full stack end-to-end. Then deploy:

1. Backend: `uv sync` → commit → push to GitHub `main` → Railway auto-deploys `zesty-delight`.
2. Frontend: `npm run build` → commit → push → Railway auto-deploys `appealing-victory`.
3. Smoke test with Stripe test card `4242 4242 4242 4242`.

The map is laid. Execute one phase at a time. Verstehst du?
