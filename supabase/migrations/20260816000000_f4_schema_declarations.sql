-- F4: declarative backfill for legal_opinions, court_forms, usage_stats,
-- users — consolidating each table's current (post all prior migrations)
-- column set, RLS, and indexes into one idempotent statement per table.
--
-- Purpose: schema-parity safety net (see scripts/parity_check.py, C-1 parity
-- job). If any of these four tables is ever missing on a target database
-- (fresh branch, DR restore), this migration reconstructs it in the shape
-- prod is in today, without depending on the full migration history being
-- replayed in order.
--
-- Every statement is IF NOT EXISTS / idempotent. Running this against prod,
-- where all four tables already exist in this shape, is a no-op. Additive
-- only — safe to apply direct per the migration policy in CLAUDE.md.
--
-- Column sources (repo migration files, cross-checked by grep — no columns
-- invented beyond what's in these files):
--   users:         20260519190000_base_schema.sql (CREATE TABLE) +
--                  20260519202500_phase_1_rls_policies.sql (RLS)
--   usage_stats:   20260519190000_base_schema.sql (CREATE TABLE) +
--                  20260519201500_phase_1_cost_instrumentation.sql (3 cols) +
--                  20260519202500_phase_1_rls_policies.sql (RLS)
--   court_forms:   20260519200447_phase_1_new_tables.sql (CREATE TABLE + RLS) +
--                  20260615235318_phase_10_form_library.sql (5 cols + index +
--                  status default) + 20260630020049_fix_court_forms_rls_status.sql
--                  (policy predicate only, no column/index change)
--   legal_opinions: 20260703020000_legal_opinions.sql (already fully
--                  idempotent — CREATE TABLE IF NOT EXISTS + indexes + RLS;
--                  restated here verbatim for a single-file schema
--                  declaration, not because the original was insufficient)

-- 1. Users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    subscription_status TEXT DEFAULT 'free',
    subscription_id TEXT,
    free_doc_used BOOLEAN DEFAULT FALSE,
    preferred_language TEXT DEFAULT 'en',
    expo_push_token TEXT,
    stripe_customer_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 2. Usage Stats
CREATE TABLE IF NOT EXISTS public.usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID,
    user_id UUID,
    document_category TEXT,
    jurisdiction TEXT,
    language TEXT,
    price_tier TEXT,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    total_input_tokens INT,
    total_output_tokens INT,
    estimated_cost_usd NUMERIC
);
ALTER TABLE public.usage_stats ENABLE ROW LEVEL SECURITY;

-- 3. Court Forms
CREATE TABLE IF NOT EXISTS public.court_forms (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_number            TEXT NOT NULL UNIQUE,
    title                  TEXT NOT NULL,
    category               TEXT NOT NULL,
    court_revision_date    TEXT,
    content_id             TEXT,
    source_download_url    TEXT,
    source_page_url        TEXT,
    situation_tags         TEXT[],
    storage_path           TEXT,
    content_hash           TEXT,
    last_checked_at        TIMESTAMPTZ,
    last_changed_at        TIMESTAMPTZ,
    status                 TEXT NOT NULL DEFAULT 'review',
    plain_language_summary TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    form_text              TEXT,
    review_reason          TEXT,
    bucket_path            TEXT
);
ALTER TABLE public.court_forms ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_court_forms_form_text_fts
  ON public.court_forms USING gin (to_tsvector('english', coalesce(form_text, '')));

-- 4. Legal Opinions
CREATE TABLE IF NOT EXISTS public.legal_opinions (
    cluster_id      TEXT,
    id              UUID DEFAULT gen_random_uuid(),
    opinion_id      TEXT,
    court_id        TEXT,
    source          TEXT,
    source_url      TEXT,
    case_name       TEXT NOT NULL DEFAULT '',
    court           TEXT NOT NULL DEFAULT '',
    date_filed      DATE,
    cite_count      INTEGER NOT NULL DEFAULT 0,
    parties         TEXT[] NOT NULL DEFAULT '{}',
    core_facts      TEXT NOT NULL DEFAULT '',
    legal_issue     TEXT NOT NULL DEFAULT '',
    holding_raw     TEXT NOT NULL DEFAULT '',
    outcome         TEXT,
    key_statutes    TEXT[] NOT NULL DEFAULT '{}',
    situation_tags  TEXT[] NOT NULL DEFAULT '{}',
    citation        TEXT,
    summary_legal   TEXT,
    summary_plain   TEXT,
    attorney_prompt TEXT,
    pass1_parsed    JSONB,
    pass2_parsed    JSONB,
    plain_text_raw  TEXT,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    quality_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    quality_notes   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_legal_opinions_situation_tags
  ON public.legal_opinions USING gin (situation_tags);
CREATE INDEX IF NOT EXISTS idx_legal_opinions_quality_flagged
  ON public.legal_opinions (quality_flagged);
ALTER TABLE public.legal_opinions ENABLE ROW LEVEL SECURITY;


-- 5. Trigger Events (declared; user_* columns removed 2026-08-18 — dropped in prod
-- by 20260817010000_g_drop_trigger_events_user_columns.sql; declaration mirrors prod)
CREATE TABLE IF NOT EXISTS public.trigger_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.documents(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_date DATE NOT NULL,
    service_method TEXT NOT NULL,
    document_type TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'FL',
    circuit INT,
    county TEXT,
    case_number TEXT,
    raw_text_excerpt TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    clerk_mailing_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.trigger_events ENABLE ROW LEVEL SECURITY;

-- 6. Document Service Facts (user-supplied service record, B5-f3)
CREATE TABLE IF NOT EXISTS public.document_service_facts (
    document_id UUID PRIMARY KEY REFERENCES public.documents(id) ON DELETE CASCADE,
    service_date DATE,
    service_method TEXT,
    clerk_mailing_date DATE,
    provenance TEXT NOT NULL DEFAULT 'extracted',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.document_service_facts ENABLE ROW LEVEL SECURITY;

NOTIFY pgrst, 'reload schema';
