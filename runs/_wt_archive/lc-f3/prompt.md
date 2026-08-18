# Dispatch F3 — disclaimer conversion batch (2 files, 3 sites)

Repo: joewpb/legalclear. Worktree: ~/code/lc-f3 (branch fix/f3-disclaimer-conversion, cut from origin/main).

## Task

Convert these files to the canonical frontend disclaimer source
(`frontend/src/components/DisclaimerNote.tsx` — read it first for the API:
named export DISCLAIMER_TEXT + default component with optional className):

1. `frontend/src/pages/DiscoveryMotionAnalyzer.tsx` — hardcoded disclaimer
   string (~line 230) → shared source.
2. `frontend/src/pages/FormsFinderFL.tsx` — TWO sites (lines ~24 and ~621) →
   shared source. Note: this page also has the "you should"→"a filer may"
   sanitizer for AI suggestions — do NOT touch that; it is unrelated to the
   disclaimer.

Style rules: keep visual placement/classes identical. Do not touch any other
file or the checker.

## Verify

`npm run build` in frontend/ must succeed. Checker frontend-duplicate count
baseline 13 → expect 10 after F2+F3 (if F2 lands first) — report the count you
see, don't fail on the exact number.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network.
No railway/supabase. Final answer: file:line of each replacement, build result,
checker delta, turn count.
