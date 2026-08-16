-- Lane C: CI migration tracking baseline. Sorts FIRST (prefix predates every
-- real migration) so the table exists before the workflow's skip-check.
--
-- Seeds every migration that was applied MANUALLY during the original build
-- (prod is live). The CI workflow records each file it applies and skips
-- anything already recorded; this seed prevents the first CI run from
-- re-applying the pre-CI era. Files deliberately NOT seeded (they must run
-- on the first CI pass): 20260813000000_add_users_and_referrals.sql (parity
-- gap — the tables do not exist in prod) and all 20260816* files.

create table if not exists public.schema_migrations (
  filename   text primary key,
  applied_at timestamptz not null default now()
);

insert into public.schema_migrations (filename) values
  ('20260519190000_base_schema.sql'),
  ('20260519200447_phase_1_new_tables.sql'),
  ('20260519201000_phase_1_fix_packets.sql'),
  ('20260519201500_phase_1_cost_instrumentation.sql'),
  ('20260519202000_phase_1_enable_pg_cron.sql'),
  ('20260519202500_phase_1_rls_policies.sql'),
  ('20260519203000_phase_1_retention_jobs.sql'),
  ('20260519210000_phase_2_storage_bucket.sql'),
  ('20260519210500_phase_2_seed_court_forms.sql'),
  ('20260519211000_phase_2_change_detection_job.sql'),
  ('20260519220000_phase_3_law_tables.sql'),
  ('20260519220500_phase_3_seed_2026_closures.sql'),
  ('20260519221000_phase_3_refresh_cron.sql'),
  ('20260519230000_phase_6_deadline_reminders.sql'),
  ('20260615235318_phase_10_form_library.sql'),
  ('20260630020049_fix_court_forms_rls_status.sql'),
  ('20260703020000_legal_opinions.sql'),
  ('20260704000000_add_filings_table.sql'),
  ('20260723120000_normalize_due_process_tag.sql'),
  ('20260808000000_seed_local_court_closures.sql'),
  ('20260811000000_add_summary_trgm_index.sql'),
  ('20260812000000_add_citation_treatment.sql'),
  ('20260814000000_add_app_config.sql'),
  ('20260815000000_b5_service_date_capture.sql'),
  ('20260815000001_b5f_clerk_mailing_date.sql'),
  ('20260815000002_b5f3_document_service_facts.sql')
on conflict (filename) do nothing;
