-- claim_facts: user-supplied policy facts, keyed by SESSION (Option A ruling 2026-08-20).
-- Drops the document_id-keyed variant applied by hand in the SQL editor before the
-- Option A ruling (it was empty; zero rows). The extraction pipeline has NO write path
-- here — only the /property-casualty/facts capture endpoint writes (enforced by test).
-- RLS enabled with NO policies is INTENTIONAL: this table is backend-service-role only.
-- Writes come from the backend using the service key (RLS bypass); no anon/authenticated
-- client path exists and none should — a policy would only matter if a user JWT ever
-- read this table directly, which the architecture never does.
drop table if exists public.claim_facts;

create table if not exists public.claim_facts (
  session_id            uuid primary key references public.sessions(id) on delete cascade,
  policy_inception_date date,
  provenance            text not null default 'user_supplied',
  updated_at            timestamptz not null default now()
);

alter table public.claim_facts enable row level security;

create index if not exists idx_claim_facts_session on public.claim_facts(session_id);
