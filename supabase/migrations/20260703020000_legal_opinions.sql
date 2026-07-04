-- legal_opinions: Florida case-law corpus ingested by the opinion-pipeline
-- (scripts/opinion_pipeline/09_write/write_to_supabase.py). The table was
-- originally created out-of-band in production; this migration captures its
-- DDL so fresh Supabase branches / `db reset` reconstruct it.
--
-- Idempotent: every statement guards with IF NOT EXISTS, so running this
-- against production (which already holds the 759-opinion corpus) is a no-op.
-- Additive-only — safe to apply direct per the migration policy.

create table if not exists public.legal_opinions (
    cluster_id      text primary key,           -- dedupe key (on_conflict target)
    case_name       text not null default '',
    court           text not null default '',
    date_filed      date,                        -- nullable when unknown
    cite_count      integer not null default 0,  -- authority signal (sort key)
    parties         text[] not null default '{}',
    core_facts      text not null default '',
    legal_issue     text not null default '',
    holding_raw     text not null default '',
    outcome         text,
    key_statutes    text[] not null default '{}',
    situation_tags  text[] not null default '{}',  -- retrieval key (.overlaps)
    citation        text,
    summary_legal   text,                        -- power-user / attorney detail
    summary_plain   text,                        -- plain-English blocks
    attorney_prompt text,                        -- dual-state next step
    quality_flagged boolean not null default false,  -- gated out of retrieval when true
    quality_notes   text not null default ''
);

-- Retrieval path: get_relevant_opinions() filters quality_flagged = false and
-- .overlaps(situation_tags, [...]). A GIN index makes the array overlap cheap.
create index if not exists idx_legal_opinions_situation_tags
  on public.legal_opinions using gin (situation_tags);
create index if not exists idx_legal_opinions_quality_flagged
  on public.legal_opinions (quality_flagged);

-- Corpus is read-only reference data served only by the backend (service-role
-- key, which bypasses RLS). Enable RLS with no policies so anon/authenticated
-- keys cannot read it directly; the service role is unaffected.
alter table public.legal_opinions enable row level security;
