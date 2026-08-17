# TASK: C-2 — author the Phase 2/3 cron GUC→app_config amendments as migration files.

Repo: root. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-c2, branch fix/c2-cron-amendments (checked out).

## Background
Phase 2/3 cron jobs were set up with Postgres GUC settings; the C3 item
says those must become app_config-driven (the app_config table is the
canonical settings store — see migration 20260814000000_add_app_config.sql).
The CI migration workflow applies supabase/migrations/*.sql in timestamp
order, so these amendments must be AUTHORED AS MIGRATION FILES to ride that
mechanism.

## Job
1. Read the existing cron/GUC setup: grep the repo for the cron jobs
   (pg_cron? cron.schedule? the backend's reminder cron) and any GUCs
   (set_config / alter role set / database settings) that Phase 2/3 added.
2. Author ONE new migration
   supabase/migrations/20260816020000_c2_cron_app_config.sql (timestamped
   after 20260816010000_d2_rls_referral_tables.sql) that declares the
   app_config rows the cron would need (matching app_config's real schema —
   key/text columns per the add_app_config migration) and any GUC-unset /
   ALTER statements that move settings off GUCs.
3. If the repo contains NO discoverable GUC/cron artifacts, author the
   app_config seed rows from what the reminder cron actually reads (the
   backend code that reads app_config — find it) and SAY SO in your report
   instead of inventing settings.

## Rules
No DDL executed — author only. No prod writes. Report: the migration file,
the repo evidence you based it on, and any settings you could NOT discover.
