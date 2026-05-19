-- Phase 2: weekly change-detection job.
-- Calls the backend's /api/forms/check-updates endpoint via pg_net.
-- BACKEND_URL is set from app.settings — replace with production URL if needed.
-- The job fires once a week (Sunday 04:00 UTC).

select cron.schedule(
  'forms-change-detection-weekly',
  '0 4 * * 0',
  $$
    select net.http_post(
      url     := current_setting('app.backend_url', true)
                 || '/api/forms/check-updates',
      headers := jsonb_build_object(
                   'Content-Type', 'application/json',
                   'X-API-Key',    current_setting('app.api_key', true)
                 ),
      body    := '{}'::jsonb
    );
  $$
);
