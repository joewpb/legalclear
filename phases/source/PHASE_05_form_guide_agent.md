# PHASE 05 — Form Guide Agent
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/agents/form_guide.py`
- Suggests which FL forms apply to a given legal situation
- Returns: `{recommended_forms: [{name, form_number, url, why}]}`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/agents/form_guide.py && echo "form_guide present"
grep -E "def suggest_forms|cache_control" backend/src/agents/form_guide.py && echo "form_guide API ok"
```

## Contract provided to later phases

- Phase 11 (FL Courts initial) and Phase 19 (Forms Finder, new) reference its output structure.
- Phase 19 uses a static JSON index instead of the live agent for v1 — Phase 19 does NOT call this agent.

## What to do if verification fails

STOP. Report the missing file.

## Final line

```
PHASE 05 VERIFIED — proceed to PHASE 06
```
