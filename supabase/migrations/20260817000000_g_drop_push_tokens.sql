-- Phase G (2026-08-17): drop push_tokens table.
-- Decision 9 deferred the mobile app; the endpoint (POST /user/{user_id}/push-token),
-- the save_push_token helper, and the empty mobile/ directory were removed in fix/g2.
-- This migration is AUTHORED BUT HELD on branch fix/g2-push-tokens-table-drop —
-- NOT merged to main yet. When merged, migrate.yml applies it via CI.
-- Idempotent.
DROP TABLE IF EXISTS public.push_tokens;
