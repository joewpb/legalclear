-- Re-drop trigger_events user_* columns (2026-08-24).
--
-- The 2026-08-23 "B5 repair" deleted schema_migrations ledger rows and re-ran
-- the B5 ADD COLUMN files AFTER G4 (20260817010000) had dropped these columns
-- — regressing G4's end-state. Decision 17: migration state repairs are
-- ALWAYS a new forward migration; ledger surgery is prohibited. This file
-- restores the G4 end-state the doctrine-clean way.
--
-- Preconditions verified 2026-08-24 against prod:
--   P2: 0 rows where user_service_date is not null or user_service_method
--       is not null.
--   Grep: no live backend code path reads or writes these columns by name
--         (response-body keys of PUT /api/deadline/{id}/service-date are
--         computed from the request, not read from trigger_events; the
--         actual write goes to document_service_facts).
--
-- clerk_mailing_date column stays (G4 never dropped it); its index goes —
-- the pipeline reads mailing dates from document_service_facts, not this
-- table.
alter table public.trigger_events
  drop column if exists user_service_date,
  drop column if exists user_service_method,
  drop column if exists service_date_provenance;

drop index if exists idx_trigger_events_user_service_date;
drop index if exists idx_trigger_events_clerk_mailing_date;
