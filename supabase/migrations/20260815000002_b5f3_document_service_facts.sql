-- B5-f3 — document_service_facts: user-supplied service facts live OFF the
-- pipeline-owned trigger_events rows (the pipeline rewrote those and clobbered
-- user columns). One row per document; the pipeline never writes this table.
-- Idempotent. Manual paste until Phase F closes G3.

create table if not exists public.document_service_facts (
  document_id         uuid primary key references public.documents(id) on delete cascade,
  service_date        date,
  service_method      text,
  clerk_mailing_date  date,
  provenance          text not null default 'user_supplied',
  updated_at          timestamptz not null default now()
);

alter table public.document_service_facts enable row level security;

create index if not exists idx_document_service_facts_document
  on public.document_service_facts(document_id);
