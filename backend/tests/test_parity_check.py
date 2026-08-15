"""Offline tests for scripts/parity_check.py (S3-1 schema parity check).

No network access — feeds fixture migration SQL and fake probe/OpenAPI
responses directly into the pure parse/diff functions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from parity_check import (  # noqa: E402
    compute_parity,
    merge_prod_sources,
    parse_migration_sql,
    parse_openapi_doc,
)

FIXTURE_SQL = """
-- fixture migration
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    subscription_status TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT now()
);

create table if not exists filings (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  document_id text,
  CONSTRAINT filings_user_fk FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attorney_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    PRIMARY KEY (id)
);
"""


def test_parse_migration_sql_extracts_tables_and_columns():
    tables = parse_migration_sql(FIXTURE_SQL)

    assert set(tables) == {"users", "filings", "attorney_inquiries"}
    assert set(tables["users"]) == {"id", "email", "subscription_status", "created_at"}
    assert tables["users"]["id"] == "UUID"


def test_parse_migration_sql_skips_table_level_constraints():
    tables = parse_migration_sql(FIXTURE_SQL)

    # FOREIGN KEY / PRIMARY KEY table-level clauses must not become columns.
    filings_cols_lower = {c.lower() for c in tables["filings"]}
    attorney_cols_lower = {c.lower() for c in tables["attorney_inquiries"]}
    assert "constraint" not in filings_cols_lower
    assert "foreign" not in filings_cols_lower
    assert "primary" not in attorney_cols_lower


def test_parse_migration_sql_strips_schema_prefix():
    tables = parse_migration_sql(FIXTURE_SQL)

    assert "users" in tables
    assert "public.users" not in tables


def test_parse_migration_sql_strips_inline_comments():
    """Regression: a trailing `-- comment` after a column def must not be
    parsed as a bogus '--' column (found live against 20260519230000 /
    20260703020000, which both use this style)."""
    sql = """
    CREATE TABLE IF NOT EXISTS deadline_reminders (
      id      uuid primary key default gen_random_uuid(),
      type    text not null,   -- '14d' | '7d' | '3d'
      channel text,            -- 'push' | 'email'
      state   text not null default 'scheduled'  -- 'scheduled' | 'sent'
    );
    """

    tables = parse_migration_sql(sql)

    assert set(tables["deadline_reminders"]) == {"id", "type", "channel", "state"}


def test_parse_openapi_doc_extracts_columns():
    doc = {
        "definitions": {
            "users": {
                "properties": {
                    "id": {"format": "uuid"},
                    "email": {"type": "string"},
                }
            }
        }
    }

    tables = parse_openapi_doc(doc)

    assert tables == {"users": {"id": "UUID", "email": "STRING"}}


def test_compute_parity_detects_missing_table():
    """RED-condition fixture: attorney_inquiries is in migrations but 404s in prod."""
    migration_tables = parse_migration_sql(FIXTURE_SQL)
    prod_tables = {
        "users": {"id": "uuid", "email": "text", "subscription_status": "text", "created_at": "timestamptz"},
        "filings": {"id": "uuid", "user_id": "text", "document_id": "text"},
        # attorney_inquiries deliberately absent -> missing table
    }

    report = compute_parity(migration_tables, prod_tables)

    assert report.missing_tables == ["attorney_inquiries"]
    assert report.extra_tables == []
    assert report.column_diffs == {}
    assert report.to_dict()["ok"] is False


def test_compute_parity_detects_extra_prod_table():
    migration_tables = {"users": {"id": "uuid"}}
    prod_tables = {
        "users": {"id": "uuid"},
        "legacy_table": {"id": "uuid"},
    }

    report = compute_parity(migration_tables, prod_tables)

    assert report.extra_tables == ["legacy_table"]
    assert report.missing_tables == []


def test_compute_parity_detects_column_diff():
    migration_tables = {"users": {"id": "uuid", "email": "text", "phone": "text"}}
    prod_tables = {"users": {"id": "uuid", "email": "text"}}  # missing "phone"; has no extra

    report = compute_parity(migration_tables, prod_tables)

    assert report.missing_tables == []
    assert report.extra_tables == []
    assert report.column_diffs == {
        "users": {"missing_columns": ["phone"], "extra_columns": []}
    }


def test_compute_parity_full_match_is_ok():
    migration_tables = {"users": {"id": "uuid", "email": "text"}}
    prod_tables = {"users": {"id": "uuid", "email": "text"}}

    report = compute_parity(migration_tables, prod_tables)

    assert report.to_dict()["ok"] is True


def test_compute_parity_empty_prod_columns_not_treated_as_all_missing():
    """A prod table probed via 404-fallback path with no sample row (empty
    table, OpenAPI silent) should not spuriously flag every migration
    column as missing — column diff is skipped when prod columns are
    unknown (empty dict)."""
    migration_tables = {"users": {"id": "uuid", "email": "text"}}
    prod_tables = {"users": {}}  # exists, but no column info available

    report = compute_parity(migration_tables, prod_tables)

    assert report.column_diffs == {}


def test_merge_prod_sources_prefers_openapi_and_falls_back_to_probe():
    openapi_tables = {"users": {"id": "UUID", "email": "STRING"}}
    probe_tables = {
        "users": {"exists": True, "columns": ["id", "email"]},
        "filings": {"exists": True, "columns": ["id", "user_id"]},
        "user_profiles": {"exists": False, "columns": []},
    }

    merged = merge_prod_sources(openapi_tables, probe_tables)

    assert merged["users"] == {"id": "UUID", "email": "STRING"}  # openapi wins
    assert set(merged["filings"]) == {"id", "user_id"}  # probe fallback
    assert "user_profiles" not in merged  # 404 -> not merged in
