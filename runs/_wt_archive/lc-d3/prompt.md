# TASK: D-3a (S1-3b backend) — gate the attorney-referral endpoints behind require_api_key.

Repo: backend/. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-d3, branch fix/d3-api-key-gate (checked out).

## Job
The attorney-referral intake and submit endpoints are currently reachable
without an API key. Gate them:
1. /intake and /submit (locate them in backend/src/api/routers/
   attorney_referral.py) must require the API key exactly like the deadline
   router does: add the dependency Depends(require_api_key) to both routes
   (the helper exists in the repo — find where require_api_key is defined
   and import it the same way other routers do).
2. Update the router's tests so unauthenticated requests to both endpoints
   return 401, and keyed requests pass (extend the existing test file for
   the router; follow the pattern from the deadline router's
   test_requires_api_key test).
3. Nothing else. Do not touch the frontend (a separate dispatch does that).

## Verification
cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 336/1 — must not drop. GREEN or STOP. (If collection fails in this
worktree because .env is absent, copy it from ~/code/legalclear/backend/.env
first — it is machine-local and gitignored.)
