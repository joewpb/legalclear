# TASK: D-2 — author RLS migration for attorney_inquiries + user_profiles.

Repo: root. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-d2, branch fix/d2-rls-migration (checked out).

## Background
Prod parity gap (recorded 20260814, migration b82e68b): the
attorney_inquiries and user_profiles tables exist in prod but were frozen
when Supabase app_config RLS was revoked — their RLS policies are
inconsistent with the rest of the schema. The CI migration workflow
(Lane C-1) will apply supabase/migrations/*.sql in timestamp order; this
migration must ride that mechanism.

## Job
Author ONE new migration file supabase/migrations/20260816010000_d2_rls_referral_tables.sql
(timestamped AFTER 20260816000000_f4_schema_declarations.sql so CI applies
the F4 declarations first, and AFTER 20260813 — the referral-tables
migration):
1. Enable RLS on attorney_inquiries and user_profiles (if not enabled).
2. Author RLS policies matching the app_config pattern the rest of the
   schema uses (read the existing migrations for the canonical policy
   shape — service-role bypasses RLS; the backend is the only writer).
   If the existing tables already have policies in prod, write the
   migration to DECLARE the intended state idempotently (drop-policy-
   if-exists + create, or create-if-not-exists per Postgres 14+ —
   prefer what the existing migrations use).
3. Add index/constraint declarations only if the repo's migration history
   shows they belong (do not invent schema).

## Note
The seconds-wide window between the two statements inside a single CI run
is ACCEPTED (recorded in the night-run spec). Do not try to "fix" it.

## Rules
No DDL executed — author only. No prod writes. Report: the migration file
content summary, which existing migrations you mirrored, and any
uncertainty about prod's current state (say so explicitly rather than
guessing).
