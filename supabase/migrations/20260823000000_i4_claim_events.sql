-- I-4 (2026-08-23): claim state machine storage — additive only.
-- 1) claims gains peril / date_of_loss / sub_type / details (user-supplied
--    facts only, JSONB — see runs/phase-i-autonomous/LOG.md D4).
-- 2) claim_events: durable, append-only trigger/flag log. The claim log
--    artifact (I-7) renders this table; the state machine (I-4) and red-flag
--    detector (I-6) read it. Nothing is ever updated or deleted here except
--    by cascade when a claim is removed.
--
-- RLS with no policies is INTENTIONAL (same ruling as claim_facts and
-- claims): backend service-role only; the claim code is the only
-- client-facing credential.

alter table public.claims
  add column if not exists peril         text not null default 'fire',
  add column if not exists date_of_loss  date,
  add column if not exists sub_type      text not null default 'first_party_property',
  add column if not exists details       jsonb not null default '{}'::jsonb;

create table if not exists public.claim_events (
  id           uuid primary key default gen_random_uuid(),
  claim_id     uuid not null references public.claims(id) on delete cascade,
  trigger_name text not null,
  occurred_at  timestamptz not null default now(),
  source       text not null default 'user',
  note         text
);

alter table public.claim_events enable row level security;

create index if not exists idx_claim_events_claim on public.claim_events(claim_id);
