You are on branch fix/s1-3-referral-auth with uncommitted work from a prior run that
exhausted its turns. The code work is done. Do not add features, do not gate any
additional endpoints, do not touch the frontend.

Already done — leave alone:
- require_api_key added to users POST and users/{user_id} GET
- backend/tests/test_attorney_referral_auth.py — 4 tests

Your only job:
1. Run `cd backend && uv run pytest tests/test_attorney_referral_auth.py -v` — must pass.
2. Run the full CI-scope suite — must be green. Exact command (this is the repo's
   definition of "the suite"; the 10 server-dependent files are excluded by design and
   fail without a live backend, which is expected and not your problem):
   `cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
   --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
   --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
   --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
   --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
   --ignore=tests/test_pc_integration.py`
3. Confirm no endpoint beyond those two was modified: `git diff --stat` — expect only
   backend/src/api/routers/attorney_referral.py modified, plus the new test file and
   FOLLOW_UPS.md untracked.
4. Report one paragraph: what changed, test counts before/after, regression risk.

Do not commit. If the suite fails, report the failure — do not fix beyond the two
endpoints already touched.
