# PHASE 13 — Mobile App (React Native / Expo)
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `mobile/` — React Native via Expo
- Same API as web (calls backend on port 8001)
- Camera document capture
- Push notifications via Expo push tokens
- Stripe payment sheet
- EN/ES toggle

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f mobile/App.tsx && echo "Mobile App.tsx present"
test -f mobile/app.json && echo "Expo config present"
grep -E "\"expo\"" mobile/package.json && echo "Expo configured ok"
```

## Contract provided to later phases

- Hub restructure (Phase 15) and new tiles (Phases 16–22) should be mirrored on mobile in a deferred v1.1 mobile pass.
- Phase 23's filing packet flow does NOT require mobile parity in v1.
- **Mobile work is OUT OF SCOPE for Phases 15–23.** Web first, then mobile catches up.

## What to do if verification fails

Note it in the final report but do NOT block. Mobile is deferred.

## Final line

```
PHASE 13 VERIFIED — proceed to PHASE 14
```
