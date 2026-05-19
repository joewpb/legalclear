-- Phase 3: statutes, court_rules, local_administrative_orders, court_closures

create table public.statutes (
  id             uuid primary key default gen_random_uuid(),
  citation       text not null unique,
  chapter        text not null,
  section        text not null,
  subsection     text,
  title          text,
  text           text not null,
  effective_date date,
  source_url     text not null,
  source_xml_ref text,
  jurisdiction   text not null default 'FL',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
alter table public.statutes enable row level security;
create index idx_statutes_citation on public.statutes(citation);
create index idx_statutes_section  on public.statutes(chapter, section);

create table public.court_rules (
  id             uuid primary key default gen_random_uuid(),
  citation       text not null unique,
  rule_set       text not null,
  rule_number    text not null,
  subsection     text,
  title          text,
  text           text not null,
  effective_date date,
  source_url     text not null,
  jurisdiction   text not null default 'FL',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
alter table public.court_rules enable row level security;
create index idx_court_rules_citation on public.court_rules(citation);
create index idx_court_rules_rule_set on public.court_rules(rule_set, rule_number);

create table public.local_administrative_orders (
  id              uuid primary key default gen_random_uuid(),
  circuit         int not null,
  ao_number       text not null,
  subject         text not null,
  effective_date  date,
  expiration_date date,
  text            text,
  summary         text,
  source_url      text not null,
  jurisdiction    text not null default 'FL',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique(circuit, ao_number)
);
alter table public.local_administrative_orders enable row level security;
create index idx_lao_circuit on public.local_administrative_orders(circuit);

create table public.court_closures (
  id           uuid primary key default gen_random_uuid(),
  circuit      int not null,
  county       text,
  closure_date date not null,
  reason       text not null,
  source       text not null,
  jurisdiction text not null default 'FL',
  created_at   timestamptz not null default now()
);
alter table public.court_closures enable row level security;
create unique index idx_court_closures_unique
  on public.court_closures(circuit, closure_date, coalesce(county, ''));
create index idx_court_closures_circuit_date on public.court_closures(circuit, closure_date);
create index idx_court_closures_date         on public.court_closures(closure_date);

create policy "authenticated_read_statutes"
  on public.statutes for select to authenticated using (true);
create policy "authenticated_read_court_rules"
  on public.court_rules for select to authenticated using (true);
create policy "authenticated_read_laos"
  on public.local_administrative_orders for select to authenticated using (true);
create policy "authenticated_read_court_closures"
  on public.court_closures for select to authenticated using (true);
