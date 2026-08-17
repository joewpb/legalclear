# TASK: B-2 (D3) — token_estimate key fix in the upload handler.

Repo: backend/. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-b2, branch fix/b2-token-estimate (checked out).

## Job
backend/src/api/routes.py around line 293 (NOT 288 — the night-run spec was
corrected) reads doc.get("token_estimate", 0) from the upload/documents
handler. Find the source of that dict — the document row or the upload
response payload — and fix the key so the token estimate actually flows
(compare with the Supabase documents table columns and the upload pipeline's
payload: the real column/key may be token_count or tokens or
estimated_tokens — verify by reading the code that PRODUCES the dict, not by
guessing). Change only what's needed to make the value correct; no other
upload-handler changes.

## Tests
Add/extend a test asserting the upload handler returns the correct token
estimate key populated from the real source (test file: backend/tests/
test_routes_upload.py or nearest existing upload test — follow the repo's
test layout).

## Verification
cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline 333/1 — must not drop. GREEN or STOP.
