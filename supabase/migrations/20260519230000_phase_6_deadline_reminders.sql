-- Phase 6: deadline_reminders table + hourly cron job

create table public.deadline_reminders (
  id          uuid primary key default gen_random_uuid(),
  deadline_id uuid not null references public.deadlines(id) on delete cascade,
  fire_at     timestamptz not null,
  type        text not null,   -- '14d' | '7d' | '3d' | '1d' | 'urgent' | 'expired'
  channel     text,            -- 'push' | 'email'
  state       text not null default 'scheduled',  -- 'scheduled' | 'sent' | 'failed'
  sent_at     timestamptz,
  created_at  timestamptz not null default now()
);
alter table public.deadline_reminders enable row level security;
create index idx_deadline_reminders_deadline on public.deadline_reminders(deadline_id);
create index idx_deadline_reminders_fire_at  on public.deadline_reminders(fire_at)
  where state = 'scheduled';

create policy "users_own_deadline_reminders"
  on public.deadline_reminders for select to authenticated
  using (
    deadline_id in (
      select d.id from public.deadlines d
      join public.documents doc on d.document_id = doc.id
      join public.sessions s   on doc.session_id = s.id
      where s.user_id = auth.uid()
    )
  );

select cron.schedule(
  'process-deadline-reminders',
  '0 * * * *',
  $$
    select net.http_post(
      url     := current_setting('app.backend_url', true)
                 || '/api/reminders/process',
      headers := jsonb_build_object(
                   'Content-Type', 'application/json',
                   'X-API-Key',    current_setting('app.api_key', true)
                 ),
      body    := '{}'::jsonb
    );
  $$
);
