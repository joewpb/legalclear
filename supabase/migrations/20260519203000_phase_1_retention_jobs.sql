-- Phase 1: pg_cron retention jobs
-- Requires phase_1_enable_pg_cron to run first.

-- Purge raw document_text 30 days after upload.
-- Fixed clock — a login does NOT reset it.
select cron.schedule(
  'purge-document-text-30d',
  '0 3 * * *',
  $$
    update public.documents
    set document_text = null
    where document_text is not null
      and created_at < now() - interval '30 days';
  $$
);

-- Purge guest sessions (user_id IS NULL) after 72 hours.
-- ON DELETE CASCADE propagates to documents, chat_messages,
-- trigger_events, and deadlines automatically.
select cron.schedule(
  'purge-guest-sessions-72h',
  '0 */6 * * *',
  $$
    delete from public.sessions
    where user_id is null
      and created_at < now() - interval '72 hours';
  $$
);
