-- Phase 1: court_forms, trigger_events, deadlines

create table public.court_forms (
  id                     uuid primary key default gen_random_uuid(),
  form_number            text not null unique,
  title                  text not null,
  category               text not null,
  court_revision_date    text,
  content_id             text,
  source_download_url    text,
  source_page_url        text,
  situation_tags         text[],
  storage_path           text,
  content_hash           text,
  last_checked_at        timestamptz,
  last_changed_at        timestamptz,
  status                 text not null default 'unverified',
  plain_language_summary text,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
alter table public.court_forms enable row level security;

create table public.trigger_events (
  id               uuid primary key default gen_random_uuid(),
  document_id      uuid references public.documents(id) on delete cascade,
  event_type       text not null,
  event_date       date not null,
  service_method   text not null,
  document_type    text not null,
  jurisdiction     text not null default 'FL',
  circuit          int,
  county           text,
  case_number      text,
  raw_text_excerpt text not null,
  confidence       numeric not null,
  created_at       timestamptz not null default now()
);
alter table public.trigger_events enable row level security;
create index idx_trigger_events_document on public.trigger_events(document_id);

create table public.deadlines (
  id                     uuid primary key default gen_random_uuid(),
  document_id            uuid references public.documents(id) on delete cascade,
  trigger_event_id       uuid references public.trigger_events(id) on delete cascade,
  label                  text not null,
  due_date               date not null,
  governing_rule         text not null,
  consequence_if_missed  text not null,
  severity               text not null,
  confidence             numeric not null,
  escalation_recommended boolean not null default false,
  computation_trace      jsonb not null,
  reminder_state         text not null default 'pending',
  created_at             timestamptz not null default now()
);
alter table public.deadlines enable row level security;
create index idx_deadlines_document on public.deadlines(document_id);
create index idx_deadlines_due_date  on public.deadlines(due_date);
