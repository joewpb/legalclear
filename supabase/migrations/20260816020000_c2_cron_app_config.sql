-- C2: move Phase 2/3/6 cron jobs off Postgres GUCs onto app_config.
--
-- Diagnosis (see runs/13_s2_5_diagnose/REPORT.md): the cron jobs added in
-- 20260519211000 (phase 2 change-detection), 20260519221000 (phase 3 statute
-- refresh), and 20260519230000 (phase 6 deadline reminders) all read
-- current_setting('app.backend_url', true) / current_setting('app.api_key', true).
-- No migration in this repo ever sets those GUCs (grep across supabase/ — zero
-- ALTER DATABASE/ROLE ... SET app.* hits). Meanwhile 20260814000000_add_app_config.sql
-- added the app_config(key, value) table specifically to hold backend_url/api_key,
-- but nothing reads it yet. Net effect: every cron run resolves the GUC to NULL and
-- posts to NULL || '/api/...' — a silent no-op.
--
-- Fix: re-schedule each job (cron.schedule with an existing job name updates it)
-- with SQL that reads from app_config instead of current_setting(). Seed rows are
-- empty placeholders per app_config's own convention (values are deployment-specific,
-- set at deploy time, never committed) — Joe must populate them in Supabase before
-- these jobs do anything.

insert into public.app_config (key, value) values
  ('backend_url', ''),
  ('api_key', '')
on conflict (key) do nothing;

-- Phase 2: weekly change-detection job — was current_setting('app.backend_url'/'app.api_key').
select cron.schedule(
  'forms-change-detection-weekly',
  '0 4 * * 0',
  $$
    select net.http_post(
      url     := (select value from public.app_config where key = 'backend_url')
                 || '/api/forms/check-updates',
      headers := jsonb_build_object(
                   'Content-Type', 'application/json',
                   'X-API-Key',    (select value from public.app_config where key = 'api_key')
                 ),
      body    := '{}'::jsonb
    );
  $$
);

-- Phase 3: annual statute refresh reminder — was current_setting('app.backend_url').
select cron.schedule(
  'statutes-refresh-annual',
  '0 9 15 6 *',
  $$
    select net.http_post(
      url     := (select value from public.app_config where key = 'backend_url')
                 || '/api/law/refresh-reminder',
      headers := jsonb_build_object('Content-Type', 'application/json'),
      body    := '{"note":"Annual statute refresh due — run ingest_statutes.py"}'::jsonb
    );
  $$
);

-- Phase 6: hourly deadline-reminder processing — was current_setting('app.backend_url'/'app.api_key').
select cron.schedule(
  'process-deadline-reminders',
  '0 * * * *',
  $$
    select net.http_post(
      url     := (select value from public.app_config where key = 'backend_url')
                 || '/api/reminders/process',
      headers := jsonb_build_object(
                   'Content-Type', 'application/json',
                   'X-API-Key',    (select value from public.app_config where key = 'api_key')
                 ),
      body    := '{}'::jsonb
    );
  $$
);
