-- Fix: court_forms RLS policy was filtering on status = 'active'
-- but Phase 10 changed the vocabulary to 'published'/'review'/'rejected'.
-- Authenticated users could see 0 of 764 forms.
--
-- Replace the old policy to include both legacy 'active' and new 'published'.

drop policy if exists "read_active_court_forms" on public.court_forms;

create policy "read_active_court_forms" on public.court_forms
  for select to authenticated
  using (status in ('active', 'published'));
