-- Fix: court_forms RLS policy was filtering on status = 'active'
-- but Phase 10 changed the vocabulary to 'published'/'review'/'rejected'.
-- Authenticated users could see 0 of 764 forms.
--
-- Replace the old policy to include both legacy 'active' and new 'published'.

drop policy if exists "read_active_court_forms" on public.court_forms;

create policy "read_active_court_forms" on public.court_forms
  for select to authenticated
  using (status in ('active', 'published'));

-- ── Revert (restore pre-fix behavior) ─────────────────────────────────────--
-- This change is policy-only — no rows are added, removed, or transformed —
-- so rolling back is a single forward migration that recreates the old
-- predicate. Run the following to undo:
--
--   drop policy if exists "read_active_court_forms" on public.court_forms;
--   create policy "read_active_court_forms" on public.court_forms
--     for select to authenticated
--     using (status = 'active');
--
-- Capture the live definition before/after (Supabase SQL Editor):
--   select polname, qual::text
--   from pg_policy
--   where polrelid = 'public.court_forms'::regclass;
--
-- Note: the service-role key bypasses RLS, so the backend (/api/forms) is
-- unaffected by this policy either way; this only governs direct
-- authenticated-client reads of court_forms.
