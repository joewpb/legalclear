# PHASE 04 — Explainer Agent
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/agents/explainer.py`
- Takes a classified document, returns plain-English summary
- Returns: `{summary, key_terms, what_to_do_next}`
- Used by Tile 1 (Upload) on the hub built in Phase 15

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/agents/explainer.py && echo "explainer present"
grep -E "def explain_document|cache_control" backend/src/agents/explainer.py && echo "explainer API ok"
```

## Contract provided to later phases

- Phase 15 hub Tile 1 routes uploads through classifier → explainer.
- Phase 23 packet builder does NOT touch this — packet templates use Jinja2 directly, not the explainer.

## What to do if verification fails

STOP. Explainer is the user-facing intelligence layer for uploads.

## Final line

```
PHASE 04 VERIFIED — proceed to PHASE 05
```
