# PHASE 00 — Project Setup
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- Project root at `~/legalclear/`
- Python venv via **uv** (no pip, ever)
- Directory structure:
  ```
  ~/legalclear/
  ├── backend/src/{agents,api,memory,services,platforms,data}/
  ├── backend/tests/
  ├── backend/pyproject.toml
  ├── backend/.env
  ├── frontend/{src,public}/
  ├── frontend/package.json
  ├── mobile/                  # React Native Expo
  ├── AGENTS.md
  └── .agent/{rules,workflows}/
  ```
- Env vars: `ANTHROPIC_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SUPABASE_URL`, `SUPABASE_KEY`, `API_KEY` (internal)

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

Run from `~/legalclear/`:

```bash
test -d backend/src/agents && test -d backend/src/api && test -d backend/src/memory && echo "backend tree ok"
test -d frontend/src && test -f frontend/package.json && echo "frontend ok"
test -f AGENTS.md && test -f .agent/workflows/run-phase.md && echo "agent rules ok"
test -f backend/pyproject.toml && echo "uv project ok"
grep -E "ANTHROPIC_API_KEY|STRIPE_SECRET_KEY|SUPABASE_URL" backend/.env && echo "env ok"
```

## Contract provided to later phases

- All later phases assume this directory tree.
- All later phases use **uv** for Python and **npm** for frontend.

## What to do if verification fails

STOP. Do not rebuild. Print the failed check and report back. The codebase is in an unexpected state — a maintainer needs to look at it.

## Final line

After running all checks above with success:
```
PHASE 00 VERIFIED — proceed to PHASE 01
```
