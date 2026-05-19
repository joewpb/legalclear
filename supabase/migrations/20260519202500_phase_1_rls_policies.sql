-- Phase 1: enable RLS and add restrictive policies on all tables

alter table public.users         enable row level security;
alter table public.sessions      enable row level security;
alter table public.documents     enable row level security;
alter table public.chat_messages  enable row level security;
alter table public.usage_stats   enable row level security;
alter table public.push_tokens   enable row level security;
alter table public.packets       enable row level security;

-- users: own record only
create policy "users_own_record" on public.users
  for all to authenticated
  using (auth.uid() = id);

-- sessions: own sessions only
create policy "users_own_sessions" on public.sessions
  for all to authenticated
  using (user_id = auth.uid());

-- documents: scoped through session join
create policy "users_own_documents" on public.documents
  for all to authenticated
  using (
    session_id in (
      select id from public.sessions where user_id = auth.uid()
    )
  );

-- chat_messages: scoped through document → session
create policy "users_own_chat_messages" on public.chat_messages
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = auth.uid()
    )
  );

-- trigger_events: scoped through document → session
create policy "users_own_trigger_events" on public.trigger_events
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = auth.uid()
    )
  );

-- deadlines: scoped through document → session
create policy "users_own_deadlines" on public.deadlines
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = auth.uid()
    )
  );

-- push_tokens: own tokens only
create policy "users_own_push_tokens" on public.push_tokens
  for all to authenticated
  using (user_id = auth.uid());

-- packets: own packets only
create policy "users_own_packets" on public.packets
  for all to authenticated
  using (user_id = auth.uid());

-- court_forms: authenticated read of active forms; writes are service-role only
create policy "read_active_court_forms" on public.court_forms
  for select to authenticated
  using (status = 'active');

-- usage_stats: no authenticated policy → service role only
