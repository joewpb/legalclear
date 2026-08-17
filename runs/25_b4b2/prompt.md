# TASK: B4b-2 — deadline.py disclaimer regression tests. Tests only (plus minimal
# helper exposure if needed). No behavioral changes.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-2-deadline-disclaimer (already checked out).

## Context
backend/src/api/routers/deadline.py is fully on apply_disclaimer already
(imports at :10; wraps at :42, :61, :81). Its external-link problem came from
apply_disclaimer's OWN text. B4b-1 (fix/b4b-1-canonicalize, unmerged) strips those
links — so a response-level link-free test would FAIL on this branch today.
Structure the tests accordingly (see below).

## Job — add regression tests proving:
1. Source-lock: the deadline router's disclaimer comes from apply_disclaimer — every
   disclaimer-bearing response path in deadline.py (analyze, deadlines list, trigger
   events list, and the ERROR path if it returns a disclaimer) has
   disclaimer == apply_disclaimer(<payload>, lang="en")["disclaimer"] output for the
   same payload shape. (Do not assert link-freeness at response level here — that
   becomes true automatically when B4b-1 merges, via the equality.)
2. Error path: when the router returns an error/exception response that carries a
   disclaimer, the disclaimer is present and equals the canonical output (find the
   actual error shapes in the file first; if an error path currently has NO
   disclaimer, report that as a finding — do not add behavior — and write the test
   for the paths that do have one).
3. Source hygiene: a test asserting the deadline.py FILE text itself contains no
   floridalawhelp / floridabar / bare http link literals (imports of other modules do
   not count — inspect the file's own string literals).
4. A brief TODO-comment test stub is NOT acceptable — every test must run and pass now.

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
- uv only. No behavioral changes to deadline.py (helper/test-dependency exposure
  allowed only if unavoidable — prefer monkeypatch). No secrets, no prod writes.
- Report: file:line of new tests, the error-path finding if any, suite count.
