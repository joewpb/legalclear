# TASK: B4d — CONTINUATION (25 turns). Finish wiring the URL filter.

Continuation of run 31_b4d (sonnet, exhausted 40 turns at $2.46).
Branch: fix/b4d-url-filter (already checked out). Do NOT redo what is done.

## Already done (VERIFIED — keep it, do not refactor)
- backend/src/core/url_filter.py (150 lines) — deterministic URL/bare-domain stripper
  with false-positive guards.
- backend/tests/test_url_filter.py (132 lines) — 15 tests, all passing (verified).
- Filter wired into 4 agents: small_claims.py, wills_trusts.py, explainer.py,
  chat_expert.py.

## Remaining job (this is the ONLY job — finish and prove, 25 turns)
1. Wire the filter into the remaining LLM text-output agent modules:
   criminal_procedure.py, discovery_motion.py, form_guide.py, expungement.py,
   police_report_v2.py, property_casualty.py. Apply the SAME wiring pattern the 4
   done agents use (read one of them to match it exactly).
   - For each, apply at the OUTPUT boundary only (final assembled text/chunks the
     user sees), never on the prompt side.
   - Structured-only outputs (risk_scanner, scanner, classifier, case_context):
     inspect each; if its output contains no free-form LLM text, state that with
     file:line evidence and skip it (do not wire blindly).
2. Extend backend/tests/test_url_filter.py with one integration-style test per newly
   wired agent asserting its output path applies the filter (use the established fake
   client pattern from test_discovery_motion.py if needed). Keep it lean — the
   utility tests already cover the regex behavior.
3. Full CI-scope suite must pass (baseline on main is 275/1 — this branch was cut
   from an earlier main, so compare against whatever its own baseline was: the 4
   wired agents' tests + 15 filter tests were green; the suite must not drop):
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: every wiring site (file:line), the structured-only skip evidence, test
  evidence, suite count, and a before/after example from one live strip.
