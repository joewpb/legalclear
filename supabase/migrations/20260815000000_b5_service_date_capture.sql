-- B5 — service date capture (Decision 2 + Decision 6, 2026-08-15)
-- Adds user-supplied service date, method, and provenance to trigger_events.
-- Idempotent. Manual paste until Phase F closes G3.

alter table public.trigger_events
  add column if not exists user_service_date date,
  add column if not exists user_service_method text,
  add column if not exists service_date_provenance text not null default 'extracted'
    check (service_date_provenance in ('extracted','user_supplied'));

create index if not exists idx_trigger_events_user_service_date
  on public.trigger_events(user_service_date);
