-- Phase 23 — packets table.
-- Source: phases/source/PHASE_23_packet_builder.md
-- Run against Supabase via the SQL editor before flipping production
-- traffic. Local dev + tests rely on the in-memory packet store in
-- src/services/packet_builder.py and do not require this migration.

CREATE TABLE IF NOT EXISTS packets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    packet_type TEXT NOT NULL,
    language TEXT NOT NULL,
    county TEXT NOT NULL,
    fee_usd NUMERIC NOT NULL,
    zip_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_payment',
    confirmation_number TEXT,
    filed_at TEXT,
    paid_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_packets_user ON packets(user_id);
CREATE INDEX IF NOT EXISTS idx_packets_status ON packets(status);
