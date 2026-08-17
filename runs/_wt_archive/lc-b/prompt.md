# TASK: B-1 (D1) — HomeHub tile + nav entry for /attorney-referral.

Repo: frontend/ is in this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-b, branch fix/d1-homehub-tile (checked out).

## Job
The attorney-referral intake (/attorney-referral, page frontend/src/pages/
AttorneyReferralFL.tsx) exists but has no discoverable entry point from the
home surface. Add:
1. A HomeHub tile (find HomeHub's tile grid — look in frontend/src for the
   home component and its tile definitions; follow the existing tile
   pattern exactly: icon, title, one-line description, route link) linking
   to /attorney-referral.
2. A nav entry wherever the other top-level flows are listed (same nav
   structure, same pattern).
Do not restyle the app. Match existing conventions; reuse the existing
attorney-referral naming (e.g. "Talk to an Attorney" — check what the page
itself uses and stay consistent).

## Verification
cd frontend && npm run build — must pass. Report the two file:line changes
and the build result. No backend changes.
