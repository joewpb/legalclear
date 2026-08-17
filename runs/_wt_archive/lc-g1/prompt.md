# Phase G, group 1 — S2-6: delete the dead /api/analyze/* router

Repo: joewpb/legalclear. Worktree: ~/code/lc-g1 (branch fix/g1-analyze-dead, cut from origin/main 849c4a5).

## Context (orchestrator pre-verified 2026-08-17)

backend/src/api/routers/analysis.py defines GET /api/analyze/{document_id} and
POST /api/analyze/stream/{document_id} ("Phase 8 — Unified analysis endpoint",
"kept for backward compatibility"). routes.py imports it (line 88) and includes
it (line 127). Orchestrator grep found ZERO callers: no frontend/src references,
no scripts/, no evals/, no backend/tests/, no services/core references.
REMEDIATION_PLAN.md S2-6 says the path is dead or broken.

## Part 1 — verify before touching (report-first)

1. Independently verify the zero-caller claim with your own greps:
   frontend/src (any "analyze" reference not belonging to other routers:
   deadline, discovery, police-report, etc.), backend/src (imports or uses of
   analysis_router / routers.analysis), scripts/, evals/, backend/tests/.
   List every hit with file:line, labeled VERIFIED or INFERRED.
2. Verify the "broken" claim: read analysis.py fully and note anything that
   would fail at runtime (e.g. DatabaseManager method mismatches, missing
   imports). State findings with file:line.
3. If you find ANY live caller — STOP. Write findings to prompt-answer.md,
   make NO edits, and exit. (The orchestrator then halts per plan.)

## Part 2 — delete (only if Part 1 confirms zero callers)

1. Delete backend/src/api/routers/analysis.py.
2. Remove the import in routes.py (~line 88) and the include_router line (~127).
3. Remove any other references Part 1 found.
4. Run the suite with the CI-scope ignores from .github/workflows/pytest.yml:
   uv run pytest tests/ -q with the exact --ignore= list that workflow uses.
   Baseline: 352 passed, 1 skipped. Any NEW failure caused by your change:
   fix it or revert that piece.
5. Report: files changed, suite result, brokenness evidence, turn count.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(no curl, no WebFetch). No railway/supabase commands. Edit files in place —
the orchestrator commits. Do NOT touch any router other than analysis.py.
Do NOT modify tests unless a test imports the deleted router (you verified
none do). Final answer must state: caller-verification result, brokenness
evidence, files changed, suite output summary.
