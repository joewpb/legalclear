# PHASE 14 — Deploy
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- Railway services:
  - `zesty-delight` — backend FastAPI
  - `appealing-victory` — frontend React/Vite
- nginx reverse proxy (where applicable)
- systemd services for any local-host deployments
- End-to-end smoke tested: upload → classify → explain → pay → download → mobile

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
# Check git remote
cd ~/legalclear && git remote -v | grep github && echo "github remote ok"

# Live health endpoint (replace [domain] with actual Railway domain)
# curl -s -o /dev/null -w "%{http_code}\n" https://[backend-domain]/health
echo "Verify Railway dashboard shows both services healthy."
```

## Contract provided to later phases

- After each Part B phase builds successfully and tests pass:
  1. `git add . && git commit -m "Phase [N] complete"`
  2. `git push origin main`
  3. Railway auto-deploys both services
  4. Wait for Railway "Deployed" status before claiming the phase done
- New env vars (e.g., none expected in Phases 15–23 — all keys already set) get added through Railway dashboard, never code.

## What to do if verification fails

If Railway services are unhealthy, STOP. Phase 15 onward can't deploy until the current state is stable.

## Final line

```
PHASE 14 VERIFIED — Part A complete.
Now proceed to PHASE 15 (start of Part B — new build).
```
