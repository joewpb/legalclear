# Dispatch F2 — disclaimer conversion batch (2 files)

Repo: joewpb/legalclear. Worktree: ~/code/lc-f2 (branch fix/f2-disclaimer-conversion, cut from origin/main).

## Task

Convert these files to the canonical frontend disclaimer source
(`frontend/src/components/DisclaimerNote.tsx` — already merged on main; read it
first to match its API: named export DISCLAIMER_TEXT + default component with
optional className):

1. `frontend/src/pages/CaseLawLookupFL.tsx` — TWO sites: the hardcoded
   disclaimer strings around lines 387 and 401 (the verify banners). Replace
   the hardcoded legal-disclaimer phrasing with the shared source. Keep the
   page's verification guidance text (that is not a disclaimer, it is the
   required verify instruction — do NOT strip it). If the two sites are the
   same string, both must come from the one constant.
2. `frontend/src/pages/CriminalProcedureExplainer.tsx` — line ~490 hardcoded
   disclaimer string → shared source.

Style rules: keep visual placement/classes identical (pass className where the
component supports it). Do not touch any other file. Do not touch the checker —
the mirror exemption is already in place.

## Verify

`npm run build` in frontend/ must succeed. `python3 scripts/verify_educational.py`
frontend-duplicate count must drop by these files (baseline 13 → expect 11).

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network.
No railway/supabase. Final answer: file:line of each replacement, build result,
checker delta, turn count.
