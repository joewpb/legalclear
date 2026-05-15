# PHASE 07 — Expungement Agent
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/agents/expungement.py`
- Walks through FL §943.0585 (expungement) / §943.059 (sealing) / §943.0584 (disqualifiers)
- Returns: `{eligible, statute, next_steps, disqualifiers}`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/agents/expungement.py && echo "expungement agent present"
grep -E "943.0585|943.059|943.0584" backend/src/agents/expungement.py && echo "FL statutes referenced ok"
```

## Contract provided to later phases

- Phase 17 (new Expungement UI) wraps this agent in a structured 5-question quiz UI.
- Phase 17 does NOT modify this agent — it calls it from a new endpoint.

## What to do if verification fails

STOP. Phase 17 depends on this agent's existence.

## Final line

```
PHASE 07 VERIFIED — proceed to PHASE 08
```
