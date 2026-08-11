-- Migration: Add GIN trigram index on summary_plain for fast ILIKE search.
-- Required for opinion_retrieval ILIKE fallback — searches all 425K summaries
-- by converting situation_tags (e.g. "self_defense" → "self defense") into
-- ILIKE patterns against the full opinion text.
--
-- Without this index, cold-start ILIKE queries on 425K rows timeout (~30s).
-- With it, queries complete in 100-600ms.

-- Enable the extension if not already active.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index on summary_plain for ILIKE / LIKE / regex searches.
-- pg_trgm supports ILIKE via trigram matching — no need for a separate
-- tsvector column or materialized view.
CREATE INDEX IF NOT EXISTS idx_opinions_summary_plain_trgm
    ON legal_opinions USING gin (summary_plain gin_trgm_ops);
