# PHASE 11 — Florida Courts Integration v1 (Mode A scaffold)
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/platforms/florida_courts.py`
- **Mode A only** — packet preparation + manual filing instructions
- **Mode B (Playwright automation) deliberately NOT built. Confirmed Path D decision.**
- Basic PDF cover sheet generation (replaced by full PDF/A pipeline in Phase 23)
- Text instructions for `myflcourtaccess.com` upload (no automation)

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · **no `myflcourtaccess.com` automation — enforced by hard test in Phase 23**.

## Verification commands

```bash
test -f backend/src/platforms/florida_courts.py && echo "florida_courts module present"
# CRITICAL: confirm Mode B was NOT built
grep -i "playwright" backend/src/platforms/florida_courts.py && echo "WARNING: Playwright reference found — must not navigate to myflcourtaccess" || echo "no playwright reference ok"
grep -i "myflcourtaccess" backend/src/platforms/florida_courts.py | grep -vi "# walkthrough text only" && echo "WARNING: unmarked myflcourtaccess reference" || echo "no unmarked myflcourtaccess refs ok"
```

## Contract provided to later phases

- **Phase 23 replaces this module's PDF generation** with the unified `packet_builder.py` + `pdfa_generator.py` (Playwright headless to PDF, never to myflcourtaccess).
- Existing endpoints continue working during transition.
- After Phase 23, `florida_courts.py` may be deprecated to a thin wrapper or removed — Phase 23 spec decides.

## What to do if verification fails

If Playwright references navigate to myflcourtaccess.com, STOP and report. That's the one boundary we never cross.

## Final line

```
PHASE 11 VERIFIED — proceed to PHASE 12
```
