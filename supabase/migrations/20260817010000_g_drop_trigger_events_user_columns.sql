-- Phase G (2026-08-17): drop trigger_events.user_* columns deprecated by B5-f3.
-- User facts live on document_service_facts; zero readers remain after the
-- deprecated db.py helpers were removed. Idempotent.
ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS user_service_date;
ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS user_service_method;
ALTER TABLE public.trigger_events DROP COLUMN IF EXISTS service_date_provenance;
