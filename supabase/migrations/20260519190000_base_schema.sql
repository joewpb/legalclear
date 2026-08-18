-- Base schema — the original out-of-band "Phase 0" tables.
--
-- These six tables (users, sessions, documents, chat_messages, push_tokens,
-- usage_stats) were applied to production out-of-band before the migration
-- system existed, so they had no migration file. Fresh
-- Supabase preview branches build schema FROM MIGRATIONS (not from a prod
-- snapshot), so Phase 1 migrations that reference them failed — e.g.
-- trigger_events.document_id → public.documents(id) (SQLSTATE 42P01).
--
-- This migration captures them so the preview branch builds cleanly. Idempotent
-- (CREATE TABLE IF NOT EXISTS): on production, where all six already exist,
-- every statement is a no-op. Safe to apply direct — additive only.
--
-- Dated 20260519190000 so it sorts BEFORE the first Phase 1 migration
-- (20260519200447_phase_1_new_tables.sql) whose FKs depend on these tables.
--
-- Source: the original out-of-band init script (deploy/supabase_schema.sql,
-- since retired in favor of this migration), with one substitution —
-- gen_random_uuid() instead of uuid_generate_v4(), to match every other
-- migration and avoid the uuid-ossp extension dependency.

-- 1. Users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    subscription_status TEXT DEFAULT 'free',
    subscription_id TEXT,
    free_doc_used BOOLEAN DEFAULT FALSE,
    preferred_language TEXT DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Sessions
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    document_filename TEXT,
    document_token_count INTEGER,
    price_tier TEXT,
    price_paid_usd INTEGER,
    payment_type TEXT,
    payment_status TEXT DEFAULT 'pending',
    stripe_payment_intent TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. Documents
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.sessions(id) ON DELETE CASCADE,
    document_text TEXT,
    classification JSONB DEFAULT '{}'::jsonb,
    explanation JSONB DEFAULT '{}'::jsonb,
    form_guide JSONB DEFAULT '{}'::jsonb,
    risk_scan JSONB DEFAULT '{}'::jsonb,
    expungement_guide JSONB DEFAULT '{}'::jsonb,
    escalation JSONB DEFAULT '{}'::jsonb,
    language TEXT DEFAULT 'en',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. Chat Messages
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.documents(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 5. Push Tokens — DROPPED 2026-08-18 by 20260817000000_g_drop_push_tokens.sql
-- (Joe's release ruling: table was empty and verified data-safe; Decision 9
-- deferred the mobile app). Declaration removed so parity matches prod.

-- 6. Usage Stats
CREATE TABLE IF NOT EXISTS public.usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_category TEXT,
    jurisdiction TEXT,
    language TEXT,
    price_tier TEXT,
    processing_time_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Refresh PostgREST schema cache now that the base tables exist.
NOTIFY pgrst, 'reload schema';
