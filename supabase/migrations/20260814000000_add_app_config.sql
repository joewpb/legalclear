-- Codify the app_config table (exists in prod outside migrations).
-- Holds per-deployment runtime configuration (backend_url, api_key) read by
-- the reminder cron (see 20260519230000_phase_6_deadline_reminders.sql).
-- Values are deployment-specific and are set at deploy time — NEVER committed.
-- RLS enabled with no policies: service role and postgres (cron) only.
-- anon/authenticated revoked entirely — this table holds a live API key.

create table if not exists public.app_config (
  key   text primary key,
  value text not null default ''
);

alter table public.app_config enable row level security;

revoke all on public.app_config from anon, authenticated;
