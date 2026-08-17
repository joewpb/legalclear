# TASK: D-1 — Decision 7: repoint all three DeepSeek call sites to Claude Haiku.

Repo: backend/. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-d, branch fix/d1-haiku-repoint (checked out).

## Job
Find every DeepSeek call site in PRODUCTION paths and repoint to Claude
Haiku. The three known sites: opinion_retrieval.py, orin_opinions.py, the
attorney-referral fallback (backend/src/api/routers/attorney_referral.py or
the agent it uses — locate by grep). Rules:
1. Haiku becomes the provider at all three sites, with the same request/
   response handling the site already has (only the provider/model
   changes).
2. Tests asserting no DeepSeek reference remains in any production path
   (grep-level test: DeepSeek may only appear in tests/docs/config
   comments that explicitly note the retirement).
3. Do not touch DEEPSEEK_API_KEY plumbing beyond making it unused in
   production paths — Joe unsets the Railway var after verification.
4. Keep the fallback structure where it exists (if a site had a
   DeepSeek fallback behind a primary, the fallback becomes Haiku too or
   is removed ONLY if the code path is dead — prefer keeping the chain
   shape, swapping the model).

## Verification
cd backend && uv run pytest tests/ -q (plus the CI-scope ignores used by the
repo). Baseline 332/1 must not drop. Report each call site file:line, the
swap made, and the anti-DeepSeek test evidence.
