# Dispatch F0 — canonical frontend disclaimer source (shared FIRST)

Repo: joewpb/legalclear. Worktree: ~/code/lc-f0 (branch fix/f0-disclaimer-component, cut from origin/main).

## Task

Build the frontend canonical disclaimer source BEFORE any conversion work.
Same pattern as B4a's shared lib/sse.ts: one module, single import everywhere.

1. Create `frontend/src/components/DisclaimerNote.tsx` — a small React
   component rendering the canonical legal-information disclaimer. Text must
   MATCH the backend canonical (backend/src/core/upl.py, DISCLAIMER_VERSION 2)
   in substance; the frontend mirror exists because a static SPA cannot import
   Python. It should:
   - Export the canonical string as a named constant (e.g. DISCLAIMER_TEXT)
     AND a component rendering it.
   - Accept no props (or minimal `className` passthrough for styling).
   - Include a short comment header: "frontend mirror of the backend canonical
     disclaimer (src/core/upl.py, DISCLAIMER_VERSION 2). If the backend text
     changes, update this mirror — the checker verifies the two stay in sync."
2. Convert exactly TWO files now as proof of the pattern (do NOT convert the
   rest — later batches do that):
   - frontend/src/components/policereport/OpinionCard.tsx (:38 area)
   - frontend/src/pages/ExpungementFL.tsx (:79 footer area)
   Replace their hardcoded disclaimer strings with the shared component, keep
   the same visual placement/classes (pass className if needed).
3. Update scripts/verify_educational.py check-4 (canonical disclaimer) as
   follows — ONLY the frontend expectation: a frontend hardcoded disclaimer
   string is a violation UNLESS it lives in
   frontend/src/components/DisclaimerNote.tsx (the canonical mirror). Add the
   mirror file to the exemption and, if easy, make the checker compare the
   mirror's text against the backend canonical's key phrases. Do not touch any
   other checker logic.

## Verify

- npm run build in frontend/ must succeed.
- Suite untouched (no backend changes).
- python3 scripts/verify_educational.py: the two converted files must drop out
  of the frontend-duplicate findings; total frontend duplicates should go from
  14 to 12 (the two converted), plus the mirror file itself is exempt.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(curl/WebFetch forbidden). No railway/supabase. Final answer: file:line of the
new component, the two conversions, checker delta, build result, turn count.
