# PHASE 10 — FastAPI Backend Consolidation
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/api/main.py` — FastAPI app on **port 8001**
- Endpoints:
  - `POST /api/upload` — PDF upload → classify + explain + risk scan
  - `POST /api/chat` — multi-turn chat about an uploaded document
  - `GET /api/eligibility` — expungement eligibility check
  - `POST /api/stripe/webhook` — payment events
  - `GET /health` — liveness
  - `POST /api/push/register` — mobile push tokens
- Auth: `X-API-Key` header required EXCEPT `/health`, `/eligibility`, `/webhook`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/api/main.py && echo "main.py present"
grep -E "uvicorn.*8001|port=8001" backend/src/api/main.py backend/pyproject.toml 2>/dev/null && echo "port 8001 ok"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/health
```

## Contract provided to later phases

- Phases 16, 17, 18, 20, 21, 22, 23 each register a new APIRouter under `/api/*`
- New routers MUST be included via `app.include_router(...)` in `main.py`
- Backend stays on **port 8001** forever. Never swap to 8000.

## What to do if verification fails

If `/health` returns anything other than 200, the backend isn't running. Start it with the existing systemd unit or the standard uv command before proceeding to any new phase.

## Final line

```
PHASE 10 VERIFIED — proceed to PHASE 11
```
