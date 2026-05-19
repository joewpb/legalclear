-- Phase 2: create Supabase Storage bucket for court forms.
-- Private bucket — all access goes through the LegalClear backend
-- using the service-role key. No direct public access.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'court-forms',
  'court-forms',
  false,
  52428800,  -- 50 MB per file
  array['application/pdf', 'application/rtf', 'text/rtf']
)
on conflict (id) do nothing;
