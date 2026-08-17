# TASK: B4b-6 — attorney_referral wrap + intake source migration. One intake path.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-6-referral-intake (already checked out).

## Context — the highest UPL-risk surface in the app
- backend/src/api/routers/attorney_referral.py: has NO disclaimer today. Decision 3 +
  B4 scope: wrap its responses with apply_disclaimer (canonical, src/core/upl.py).
- backend/src/api/routers/intake.py:16: uses get_disclaimer (now a delegator to
  apply_disclaimer on the B4b-1 branch — unmerged). On this branch get_disclaimer is
  the old source; migrate intake to import apply_disclaimer DIRECTLY so the canonical
  source is explicit at the call site.
- NOTE on branch isolation: B4b-1 (canonicalization, fix/b4b-1-canonicalize,
  88dea23) is UNMERGED. Do not depend on it. Call apply_disclaimer as it exists on
  main today; the canonicalization merge will strip links later. Your job is
  plumbing: the RIGHT source function, the RIGHT wrap, tests that survive the
  canonicalization merge (assert equality-with-apply_disclaimer, not specific text).

## Job
1. attorney_referral.py: find EVERY user-facing response path (the chat/submit
   responses, error paths included where they return content) and wrap with
   apply_disclaimer in the same style as the other routers (see case_law.py:262,
   packet.py:62 for the established call shape). The chat STREAMING path (if any)
   must keep working — apply the wrap at response composition, not inside the stream
   unless the stream shape already supports it; if the stream cannot carry a
   disclaimer field, report that limitation instead of breaking it.
2. intake.py: swap get_disclaimer → apply_disclaimer with the correct signature
   (apply_disclaimer(payload_dict, lang=..., level=...)) — keep the same disclaimer
   text level (standard) and language behavior as before.
3. Tests (red→green): attorney_referral responses (success + at least one error path)
   carry disclaimer == apply_disclaimer(...)["disclaimer"]; intake behaves
   identically to before the swap. Follow existing router test patterns.

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 249/1 — must not drop.

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: file:line of every wrap, the streaming-path limitation (if any), test
  evidence, suite count.
