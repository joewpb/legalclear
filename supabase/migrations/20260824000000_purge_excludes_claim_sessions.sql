-- Purge exclusion (2026-08-24): the 72h anonymous-session purge cascaded into
-- claim_facts (ON DELETE CASCADE), destroying policy_inception_date — the sole
-- anchor for the pre/post-2022-12-16 regime switch. User-supplied facts are B5
-- doctrine; a retention cron may not destroy them.
--
-- Replaces the job created in 20260519203000_phase_1_retention_jobs.sql as
-- 'purge-guest-sessions-72h' with a claim-aware predicate: sessions that back
-- claim_facts or claims are never purged. (claims.session_id is SET NULL, so
-- claim rows survived the old purge but were severed from their facts.)
--
-- jobid 2 is NOT assumed stable — unschedule by jobname match.
select cron.unschedule(jobid)
from cron.job
where jobname = 'purge-guest-sessions-72h';

select cron.schedule(
  'purge_anonymous_sessions',
  '0 */6 * * *',
  $$
  delete from public.sessions s
  where s.user_id is null
    and s.created_at < now() - interval '72 hours'
    and not exists (select 1 from public.claim_facts cf where cf.session_id = s.id)
    and not exists (select 1 from public.claims c      where c.session_id = s.id);
  $$
);
