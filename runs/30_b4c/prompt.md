# TASK: B4c — rewrite test_pc_upl against the canonical source. Tests only.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4c-pc-upl-rewrite (already checked out).

## Context
The deferred branch fix/pc-upl-stale-tests (71601f4) rewrote
backend/tests/test_pc_upl.py to import get_disclaimer from src/core/upl.py with
signature ("standard", "en") — conflicting with main's current state, so it was
deferred to B4. Decision 3 now makes apply_disclaimer (src/core/upl.py) the canonical
source, and get_disclaimer (src/core/disclaimer.py) a delegator (B4b-1 branch,
unmerged). The deferred branch is NOT to be merged as written — expect to REWRITE the
test file fresh against the canonical source.

## Job
1. Inspect main's current backend/tests/test_pc_upl.py and the deferred branch's
   version (git show fix/pc-upl-stale-tests:backend/tests/test_pc_upl.py). Report in
   one paragraph: which assertions from the deferred branch are still valuable, which
   are stale, and why the file must be rewritten rather than merged.
2. Rewrite backend/tests/test_pc_upl.py ON THIS BRANCH (starting from main's current
   version) so that:
   - Every disclaimer assertion imports apply_disclaimer from src.core.upl and
     asserts equality-with-canonical output (never literal disclaimer text — must
     survive the B4b-1 canonicalization merge, which strips links and bumps
     DISCLAIMER_VERSION).
   - The deferred branch's valuable intent (behavioral UPL audit assertions, not
     source-structure assertions) is preserved.
   - The file passes against main TODAY (B4b-1 unmerged) and will pass after
     canonicalization merges.
3. Report whether the deferred branch was rewritten or superseded, with the reasoning.

## Verification
Run this file and the full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 249/1 — must not drop.

## Rules
- uv only. Test files only. No migrations, no secrets.
- Report: the assessment paragraph, what was rewritten, test evidence, suite count,
  and the rewrite-vs-supersede verdict.
