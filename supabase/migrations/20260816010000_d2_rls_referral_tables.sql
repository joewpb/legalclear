-- D-2: RLS parity fix for attorney_inquiries and user_profiles.
--
-- These tables (20260813000000_add_users_and_referrals.sql) were created
-- without RLS statements and were frozen when Supabase app_config RLS was
-- revoked — recorded as a prod parity gap 20260814 (migration b82e68b).
-- Neither table has a Supabase-auth-linked owner column (user_profiles.id
-- is a standalone gen_random_uuid(), not auth.uid()), and neither is read
-- by an authenticated browser client — only the backend
-- (backend/src/api/routers/attorney_referral.py, via the service-role key)
-- reads or writes them. That makes these service-role-only tables, the
-- same shape as app_config (20260814000000_add_app_config.sql): RLS
-- enabled, no authenticated/anon policies, and anon/authenticated
-- explicitly revoked.
--
-- Declared idempotently (IF NOT EXISTS / DROP POLICY IF EXISTS-then-CREATE)
-- per the F4 schema-declarations convention
-- (20260816000000_f4_schema_declarations.sql), so this migration is a
-- no-op if prod's current policies already match.

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attorney_inquiries ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.user_profiles FROM anon, authenticated;
REVOKE ALL ON public.attorney_inquiries FROM anon, authenticated;
