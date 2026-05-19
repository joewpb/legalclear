-- Phase 3: annual statute refresh reminder (June 15, after FL legislative session).

select cron.schedule(
  'statutes-refresh-annual',
  '0 9 15 6 *',
  $$
    select net.http_post(
      url     := current_setting('app.backend_url', true)
                 || '/api/law/refresh-reminder',
      headers := jsonb_build_object('Content-Type', 'application/json'),
      body    := '{"note":"Annual statute refresh due — run ingest_statutes.py"}'::jsonb
    );
  $$
);
