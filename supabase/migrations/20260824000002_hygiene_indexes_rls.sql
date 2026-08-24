-- Hygiene: indexes, duplicate index, missing FK, RLS initplan (2026-08-24).
-- One concern per part; every statement idempotent or database-validated.

-- Part A — indexes for unindexed FKs (Supabase advisor:
-- unindexed_foreign_keys). Each guards with IF NOT EXISTS.
create index if not exists idx_documents_session_id      on public.documents(session_id);
create index if not exists idx_sessions_user_id          on public.sessions(user_id);
create index if not exists idx_chat_messages_document_id on public.chat_messages(document_id);
create index if not exists idx_deadlines_trigger_event   on public.deadlines(trigger_event_id);
create index if not exists idx_claims_session_id         on public.claims(session_id);

-- Part B — duplicate index on legal_opinions.situation_tags. GUARDED: drop
-- idx_situation_tags only when the repo-declared GIN index also exists, so
-- this can never leave the column unindexed (self-validating check — a
-- check that can pass silently is not a check).
do $$
begin
  if exists (select 1 from pg_indexes where indexname = 'idx_situation_tags')
     and exists (select 1 from pg_indexes
                where indexname = 'idx_legal_opinions_situation_tags')
  then
    drop index idx_situation_tags;
  end if;
end $$;

-- Part C — missing FK citation_treatment.cluster_id -> legal_opinions.
-- Prod column types are integer/integer (probed via OpenAPI 2026-08-24);
-- the 20260703020000 file's TEXT declaration drifted from prod and parity
-- diffs names only, so the drift went unseen. Orphans verified 0 across
-- the sampled set, and the ALTER itself fails loudly on any orphan — the
-- database enforces the precondition, not a probe.
alter table public.citation_treatment
  add constraint citation_treatment_cluster_id_fkey
  foreign key (cluster_id) references public.legal_opinions(cluster_id)
  on delete cascade;

-- Part D — RLS initplan (Supabase advisor: auth_rls_initplan). auth.uid()
-- re-evaluates per row inside policy predicates; wrapping it in a scalar
-- subquery makes it an initplan evaluated once per query. Role, command,
-- and predicate preserved exactly as declared in the repo
-- (20260519202500_phase_1_rls_policies.sql,
--  20260519230000_phase_6_deadline_reminders.sql).
-- NOTE: users_own_deadline_reminders is FOR SELECT (not ALL) — preserved.

drop policy if exists "users_own_record" on public.users;
create policy "users_own_record" on public.users
  for all to authenticated
  using ((select auth.uid()) = id);

drop policy if exists "users_own_sessions" on public.sessions;
create policy "users_own_sessions" on public.sessions
  for all to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "users_own_packets" on public.packets;
create policy "users_own_packets" on public.packets
  for all to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "users_own_documents" on public.documents;
create policy "users_own_documents" on public.documents
  for all to authenticated
  using (
    session_id in (
      select id from public.sessions where user_id = (select auth.uid())
    )
  );

drop policy if exists "users_own_chat_messages" on public.chat_messages;
create policy "users_own_chat_messages" on public.chat_messages
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = (select auth.uid())
    )
  );

drop policy if exists "users_own_trigger_events" on public.trigger_events;
create policy "users_own_trigger_events" on public.trigger_events
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = (select auth.uid())
    )
  );

drop policy if exists "users_own_deadlines" on public.deadlines;
create policy "users_own_deadlines" on public.deadlines
  for all to authenticated
  using (
    document_id in (
      select d.id from public.documents d
      join public.sessions s on d.session_id = s.id
      where s.user_id = (select auth.uid())
    )
  );

drop policy if exists "users_own_deadline_reminders" on public.deadline_reminders;
create policy "users_own_deadline_reminders"
  on public.deadline_reminders for select to authenticated
  using (
    deadline_id in (
      select d.id from public.deadlines d
      join public.documents doc on d.document_id = doc.id
      join public.sessions s   on doc.session_id = s.id
      where s.user_id = (select auth.uid())
    )
  );
