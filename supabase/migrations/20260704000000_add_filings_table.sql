-- Add the `filings` table queried by DatabaseManager.count_filings /
-- record_filing (backend/src/memory/db.py) via POST /florida-filing/prepare.
-- The backend has referenced this table since v1 but no migration ever
-- created it — on a schema built purely from migrations those queries fail.
--
-- Column types match exactly what db.py writes: user_id arrives as a raw
-- request-header string (not guaranteed to be a uuid), document_id may be
-- an empty string — so both are text, not uuid FKs.
--
-- Additive-only: safe for direct apply per repo migration policy.

create table if not exists public.filings (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  document_id text,
  filing_type text not null default 'florida',
  jurisdiction text not null default 'FL',
  created_at  timestamptz not null default now()
);

create index if not exists idx_filings_user on public.filings(user_id);

-- Written and read only by the backend (service role, bypasses RLS).
-- No authenticated policy on purpose — same pattern as usage_stats.
alter table public.filings enable row level security;
