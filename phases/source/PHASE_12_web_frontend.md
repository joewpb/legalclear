# PHASE 12 — Web Frontend v1
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `frontend/` — React + Vite + Tailwind
- Original routes (pre-restructure):
  - `/` — Upload-first landing (REPLACED in Phase 15)
  - `/results/:id` — Upload results with 6 tabs (Summary, Key Terms, Risks, Forms, Chat, Expungement)
  - `/subscription` — Stripe checkout
- EN/ES toggle (frontend only — Phase 23 deepens this with backend-side templates)
- Deployed on Railway as `appealing-victory`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f frontend/src/App.tsx && echo "App.tsx present"
test -f frontend/package.json && echo "package.json present"
grep -E "VITE_API_URL" frontend/ -r && echo "API URL env wired ok"
grep -E "react-router-dom" frontend/package.json && echo "router ok"
cd frontend && npm run build 2>&1 | tail -3
```

## Contract provided to later phases

- **Phase 15 RESTRUCTURES `/`** to be a HomeHub. The existing `/results/:id` and `/subscription` routes are preserved.
- New tile pages (Phases 15–22) and FilingPacket page (Phase 23) get added.
- Phase 15 establishes the Brutalist design system that EVERY new component from Phase 15 onward must use.

## What to do if verification fails

If `npm run build` fails, STOP — the frontend can't be deployed. Report which packages are broken.

## Final line

```
PHASE 12 VERIFIED — proceed to PHASE 13
```
