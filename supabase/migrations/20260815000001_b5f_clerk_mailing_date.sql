-- B5-f — persist clerk_mailing_date for posted service (Decision 6, 2026-08-15)
-- Idempotent. Manual paste until Phase F closes G3.

alter table public.trigger_events
  add column if not exists clerk_mailing_date date;

create index if not exists idx_trigger_events_clerk_mailing_date
  on public.trigger_events(clerk_mailing_date);
