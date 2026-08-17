# TASK: B4b-1a — remove agent-prompt link instructions, then VERIFY AT THE OUTPUT LEVEL.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-1a-agent-prompts (already checked out).

## Background
Two agent prompts instruct the LLM to print an external link:
- backend/src/agents/explainer.py:35 — "Free help: floridalawhelp.org."
- backend/src/agents/form_guide.py:23 — same instruction.
The no-external-links rule requires removing the instruction — but removal is NOT
proof. The model may still emit the URL from training data. You must verify at the
OUTPUT level.

## Job
1. Edit the two prompt lines: replace the floridalawhelp.org instruction with the
   on-site reference using the established wording (search the codebase for
   find-legal-help phrasing — e.g. "Free help: LegalClear /find-legal-help"). Keep the
   rest of each prompt byte-identical.
2. Then ACTUALLY RUN each affected agent against a representative input and grep the
   produced text for floridalawhelp, floridabar, and bare http:// or https:// strings.
   - Find how each agent is invoked (they live behind streaming routers; find their
     entry methods and construct the minimal valid call). Use uv run python scripts —
     the backend .env provides ANTHROPIC_API_KEY on this machine. Write a small throwaway
     script under /tmp (NOT committed) that calls explainer.py's entry and
     form_guide.py's entry with a representative English prompt (e.g. a simple eviction
     question for explainer; a "how do I file a small claim" question for form_guide),
     then print the returned text and the grep results.
   - If the produced text contains floridalawhelp, floridabar, or ANY bare external
     URL: STOP. Do not try to fix it by prompt-tuning. Report exactly what the model
     produced (quote it) — that is a different problem (model-level link emission)
     which needs its own decision.
   - If clean: report the produced text excerpts as evidence.
3. No test-suite changes are REQUIRED (prompt text edits are not unit-tested in this
   repo per convention) — but run the CI-scope suite to prove nothing broke:
   cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py

## Rules
- uv only. Commit only the two prompt-file edits (no /tmp scripts, no secrets).
- Report: file:line of both edits, the exact new wording, the VERBATIM grep results of
  the live agent outputs (or the STOP flag with quoted model text), suite count.
