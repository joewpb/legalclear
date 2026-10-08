-- 2026-10-08: pg_trgm indexes — SELF-HEALING re-application.
--
-- History: 20260811000000_add_summary_trgm_index.sql is ledger-recorded as
-- applied, but live prod timing probes (Oct 2-8) show rare-term ILIKE still
-- full-scanning the 425K-row heap (~8.7-9.5s), i.e. the index is missing or
-- unusable in prod. PostgREST has no SQL path from outside; this migration
-- runs server-side via the Migrations CI (Management API) so the DDL lands
-- in the correct project regardless of dashboard state.
--
-- All statements are idempotent; ANALYZE refreshes planner statistics after
-- the large Oct 2 backfill so the planner will actually choose the index.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_opinions_summary_plain_trgm
    ON legal_opinions USING gin (summary_plain gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_opinions_case_name_trgm
    ON legal_opinions USING gin (case_name gin_trgm_ops);

ANALYZE legal_opinions;

-- Evidence for the CI log: the index rows must appear in the response.
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename = 'legal_opinions'
  AND indexname LIKE '%trgm%'
ORDER BY indexname;
