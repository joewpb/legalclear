-- Migration: citation treatment table for negative case law treatment.
-- Stores parentheticals from CourtListener indicating a FL case was
-- overruled, reversed, superseded, criticized, etc.
CREATE TABLE IF NOT EXISTS citation_treatment (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    treatment_type TEXT NOT NULL,
    treatment_text TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'described',
    score REAL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ct_cluster
    ON citation_treatment (cluster_id);

CREATE INDEX IF NOT EXISTS idx_ct_type
    ON citation_treatment (treatment_type);
