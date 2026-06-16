-- Phase 10: FL court-forms library ingest support.
-- Adds raw-text + enrichment + gating columns to court_forms.
-- Idempotent: safe to re-run.

alter table public.court_forms add column if not exists form_text              text;
alter table public.court_forms add column if not exists plain_language_summary text;       -- filled by enrichment writeback
alter table public.court_forms add column if not exists situation_tags         text[];     -- filled by enrichment writeback
alter table public.court_forms add column if not exists review_reason          text;       -- why a row is gated (null when published)
alter table public.court_forms add column if not exists bucket_path            text;        -- storage object path of the canonical PDF

-- New gating vocabulary for this library: 'published' (servable) | 'review' (gated).
-- Legacy values ('active','unverified','stale','withdrawn') remain valid; the
-- forms router treats both 'published' and 'active' as servable.
alter table public.court_forms alter column status set default 'review';

-- Full-text search over the extracted form text (used by in-app form search).
create index if not exists idx_court_forms_form_text_fts
  on public.court_forms using gin (to_tsvector('english', coalesce(form_text, '')));
