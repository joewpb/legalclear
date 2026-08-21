-- claims: durable, anonymously-resumable claim records (I-2d, Joe 2026-08-21).
-- The claim CODE is a credential: issued as 128-bit urlsafe random, stored
-- ONLY as sha256(code) — a DB leak reveals nothing usable. Not sequential.
-- G2 account-linking (scoped, NOT built here): user_id is the link point —
-- when accounts exist, POST /api/claims/{code}/link sets user_id (once,
-- only if null) so an existing code joins the account instead of being
-- stranded. Do not add any other mechanism here.
create table if not exists public.claims (
  id               uuid primary key default gen_random_uuid(),
  code_hash        text unique not null,
  user_id          uuid references public.users(id) on delete set null,
  session_id       uuid references public.sessions(id) on delete set null,
  phase            text not null default 'fire.p0.immediate',
  phase_entered_at timestamptz not null default now(),
  created_at       timestamptz not null default now(),
  last_seen_at     timestamptz not null default now()
);
alter table public.claims enable row level security;
create index if not exists idx_claims_user on public.claims(user_id);
-- RLS with no policies is INTENTIONAL (same ruling as claim_facts): backend
-- service-role only; the code is the only client-facing credential.
