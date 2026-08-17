"""Schema parity check: supabase/migrations/*.sql vs prod schema (S3-1).

Read-only. Makes no writes to prod. Reads SUPABASE_URL and
SUPABASE_SERVICE_KEY from the environment (or backend/.env via
python-dotenv, same loader backend/src/core/config.py uses) and never
prints or logs the key itself.

Usage (from repo root):

    uv run --project backend python scripts/parity_check.py
    uv run --project backend python scripts/parity_check.py --json out.json
    uv run --project backend python scripts/parity_check.py --migrations-dir supabase/migrations

What it does:
  1. Parses every `CREATE TABLE [IF NOT EXISTS] [schema.]name (...)` stanza
     in supabase/migrations/*.sql with a plain-text parser (see
     `parse_migration_sql` docstring for its documented limits — it does
     NOT understand ALTER TABLE ADD COLUMN, so a column added via ALTER
     rather than CREATE will not appear in the migration-side schema).
  2. Probes prod read-only two ways:
       a. GET {SUPABASE_URL}/rest/v1/ with an OpenAPI accept header —
          PostgREST returns exposed tables + column names/types.
       b. GET {SUPABASE_URL}/rest/v1/{table}?select=*&limit=1 per table —
          confirms existence (200 vs 404) and, if a row comes back, its
          column keys. An empty table yields no columns from this probe
          (limitation: relies on (a) to fill that gap).
  3. Diffs the two schemas: missing tables, extra prod tables, and
     column-level differences per table present on both sides.
  4. Prints a human-readable report and, with --json, writes a
     machine-readable summary for CI.

No migration file is modified. No prod writes of any kind are made.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- constraint/keyword lines inside a CREATE TABLE body that are NOT
# column definitions. Matched case-insensitively against the first token(s).
_NON_COLUMN_STARTS = (
    "primary key",
    "foreign key",
    "unique",
    "check",
    "constraint",
    "exclude",
)

_CREATE_TABLE_RE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?"
    r"(?P<name>[a-zA-Z0-9_.\"]+)\s*\(",
    re.IGNORECASE,
)


def _strip_schema_prefix(table_name: str) -> str:
    name = table_name.replace('"', "")
    if "." in name:
        name = name.split(".")[-1]
    return name


def _split_top_level_commas(body: str) -> list[str]:
    """Split a CREATE TABLE body into column/constraint clauses.

    Splits on commas that are not nested inside parentheses (e.g. inside
    a DEFAULT '(...)' expression, CHECK (...), or REFERENCES tbl(col)).
    """
    parts = []
    depth = 0
    current = []
    for ch in body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _extract_table_body(sql: str, open_paren_index: int) -> tuple[str, int]:
    """Given the index of the `(` that opens a CREATE TABLE body, return
    (body_text, index_just_after_the_matching_close_paren)."""
    depth = 0
    start = open_paren_index
    for i in range(open_paren_index, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                return sql[start + 1 : i], i + 1
    raise ValueError("unbalanced parentheses in CREATE TABLE statement")


def _strip_line_comments(sql: str) -> str:
    """Remove `-- ...` line comments, respecting single-quoted string
    literals (so a literal containing `--` is left intact)."""
    out = []
    in_string = False
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if in_string:
            out.append(ch)
            if ch == "'":
                in_string = False
            i += 1
            continue
        if ch == "'":
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            while i < n and sql[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_migration_sql(sql: str) -> dict[str, dict[str, str]]:
    """Parse CREATE TABLE stanzas out of one migration file's SQL text.

    Returns {table_name: {column_name: column_type}}.

    Limits (documented, not fixed — this is a plain-text parser, not a
    SQL parser):
      - Only understands `CREATE TABLE [IF NOT EXISTS] name (...)`.
        ALTER TABLE (ADD COLUMN, DROP COLUMN, etc.) is not tracked.
      - Column type is taken as everything after the column name up to
        the first recognized constraint keyword (PRIMARY KEY, REFERENCES,
        NOT NULL, DEFAULT, UNIQUE, CHECK) — good enough for a base-type
        diff (e.g. TEXT vs UUID) but not a full type-modifier parse.
      - Table-level constraints (PRIMARY KEY (...), FOREIGN KEY (...),
        CONSTRAINT ..., UNIQUE (...), CHECK (...)) are skipped as
        non-column clauses via a keyword prefix match.
      - Does not evaluate `schema.table` beyond stripping the schema
        prefix — `public.users` and `users` are treated as the same
        table.
    """
    sql = _strip_line_comments(sql)
    tables: dict[str, dict[str, str]] = {}
    for match in _CREATE_TABLE_RE.finditer(sql):
        table_name = _strip_schema_prefix(match.group("name"))
        open_paren = match.end() - 1
        body, _ = _extract_table_body(sql, open_paren)
        columns: dict[str, str] = {}
        for clause in _split_top_level_commas(body):
            clause_lower = clause.strip().lower()
            if any(clause_lower.startswith(kw) for kw in _NON_COLUMN_STARTS):
                continue
            tokens = clause.split()
            if not tokens:
                continue
            col_name = tokens[0].replace('"', "")
            rest = tokens[1:]
            type_tokens: list[str] = []
            stop_words = {
                "primary",
                "references",
                "not",
                "default",
                "unique",
                "check",
                "constraint",
                "generated",
            }
            for tok in rest:
                if tok.lower() in stop_words:
                    break
                type_tokens.append(tok)
            columns[col_name] = " ".join(type_tokens).upper()
        tables.setdefault(table_name, {}).update(columns)
    return tables


def parse_migrations_dir(migrations_dir: Path) -> dict[str, dict[str, str]]:
    """Parse every *.sql file in migrations_dir, in filename (timestamp) order."""
    tables: dict[str, dict[str, str]] = {}
    for path in sorted(migrations_dir.glob("*.sql")):
        file_tables = parse_migration_sql(path.read_text())
        for name, cols in file_tables.items():
            tables.setdefault(name, {}).update(cols)
    return tables


# --------------------------------------------------------------------------
# Prod probing (network I/O isolated here so the parser/differ stay testable
# offline with no network).
# --------------------------------------------------------------------------


def fetch_openapi_schema(base_url: str, service_key: str) -> dict[str, dict[str, str]]:
    """GET {base_url}/rest/v1/ with an OpenAPI accept header.

    Returns {table_name: {column_name: column_type}} parsed from the
    OpenAPI `definitions` section. Returns {} on any failure (network,
    non-200, unexpected shape) — the per-table probe is the fallback.
    """
    url = base_url.rstrip("/") + "/rest/v1/"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/openapi+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return {}
    return parse_openapi_doc(doc)


def parse_openapi_doc(doc: dict) -> dict[str, dict[str, str]]:
    """Pure parse of a PostgREST OpenAPI document -> {table: {col: type}}."""
    tables: dict[str, dict[str, str]] = {}
    definitions = doc.get("definitions", {})
    for table_name, definition in definitions.items():
        properties = definition.get("properties", {})
        tables[table_name] = {
            col: (prop.get("format") or prop.get("type") or "").upper()
            for col, prop in properties.items()
        }
    return tables


def probe_table(base_url: str, service_key: str, table: str) -> tuple[bool, list[str]]:
    """Per-table REST probe: select=*&limit=1.

    Returns (exists, column_keys). column_keys is [] if the table is
    empty or the probe failed to parse a row — an empty result here does
    NOT imply the table has no columns, only that this probe found none.
    """
    url = f"{base_url.rstrip('/')}/rest/v1/{table}?select=*&limit=1"
    req = urllib.request.Request(
        url,
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, []
        raise
    if status != 200:
        return False, []
    try:
        rows = json.loads(body.decode("utf-8"))
    except ValueError:
        return True, []
    if isinstance(rows, list) and rows:
        return True, list(rows[0].keys())
    return True, []


def probe_prod_schema(
    base_url: str, service_key: str, candidate_tables: list[str]
) -> dict[str, dict[str, object]]:
    """Probe each candidate table. Returns {table: {"exists": bool, "columns": [...]}}."""
    result: dict[str, dict[str, object]] = {}
    for table in candidate_tables:
        exists, columns = probe_table(base_url, service_key, table)
        result[table] = {"exists": exists, "columns": columns}
    return result


# --------------------------------------------------------------------------
# Diff (pure, testable offline)
# --------------------------------------------------------------------------


@dataclass
class ParityReport:
    missing_tables: list[str] = field(default_factory=list)
    extra_tables: list[str] = field(default_factory=list)
    column_diffs: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "missing_tables": sorted(self.missing_tables),
            "extra_tables": sorted(self.extra_tables),
            "column_diffs": self.column_diffs,
            "ok": not self.missing_tables and not self.extra_tables and not self.column_diffs,
        }


def compute_parity(
    migration_tables: dict[str, dict[str, str]],
    prod_tables: dict[str, dict[str, str]],
) -> ParityReport:
    """Diff migration-derived schema against prod-derived schema.

    Both args are {table_name: {column_name: column_type}}. A prod table
    with an empty column dict is treated as "exists, columns unknown" —
    it will not generate spurious missing-column findings.
    """
    report = ParityReport()
    migration_names = set(migration_tables)
    prod_names = set(prod_tables)

    report.missing_tables = sorted(migration_names - prod_names)
    report.extra_tables = sorted(prod_names - migration_names)

    for table in sorted(migration_names & prod_names):
        prod_cols = prod_tables[table]
        if not prod_cols:
            continue  # columns unknown for this table; nothing to diff
        mig_cols = migration_tables[table]
        missing_cols = sorted(set(mig_cols) - set(prod_cols))
        extra_cols = sorted(set(prod_cols) - set(mig_cols))
        if missing_cols or extra_cols:
            report.column_diffs[table] = {
                "missing_columns": missing_cols,
                "extra_columns": extra_cols,
            }
    return report


def merge_prod_sources(
    openapi_tables: dict[str, dict[str, str]],
    probe_tables: dict[str, dict[str, object]],
) -> dict[str, dict[str, str]]:
    """Merge OpenAPI columns (authoritative when present) with probe
    existence/columns (fallback for tables OpenAPI didn't expose, e.g. RLS-hidden)."""
    merged: dict[str, dict[str, str]] = {name: dict(cols) for name, cols in openapi_tables.items()}
    for table, info in probe_tables.items():
        if not info["exists"]:
            continue
        if table not in merged:
            merged[table] = {col: "" for col in info["columns"]}
    return merged


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _load_env() -> tuple[str, str]:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / "backend" / ".env")
    except ImportError:
        pass
    # GitHub-secret pastes routinely carry a trailing newline; urllib rejects
    # hostnames with control characters (InvalidURL). Strip whitespace from
    # both values on load.
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    return url, key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=REPO_ROOT / "supabase" / "migrations",
    )
    parser.add_argument("--json", type=Path, default=None, help="write machine-readable report here")
    args = parser.parse_args(argv)

    url, key = _load_env()
    if not url or not key:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set "
            "(environment or backend/.env). Refusing to run without them.",
            file=sys.stderr,
        )
        return 2

    migration_tables = parse_migrations_dir(args.migrations_dir)
    print(f"Parsed {len(migration_tables)} table(s) from {args.migrations_dir}")

    openapi_tables = fetch_openapi_schema(url, key)
    print(f"OpenAPI probe returned {len(openapi_tables)} table(s)")

    probe_tables = probe_prod_schema(url, key, sorted(migration_tables))
    prod_tables = merge_prod_sources(openapi_tables, probe_tables)

    report = compute_parity(migration_tables, prod_tables)
    summary = report.to_dict()

    print()
    print("=== Schema Parity Report ===")
    print(f"Tables in migrations but missing in prod: {summary['missing_tables'] or 'none'}")
    print(f"Tables in prod but not in migrations:      {summary['extra_tables'] or 'none'}")
    if summary["column_diffs"]:
        print("Column-level diffs:")
        for table, diff in summary["column_diffs"].items():
            print(f"  {table}: missing={diff['missing_columns']} extra={diff['extra_columns']}")
    else:
        print("Column-level diffs: none")
    print()
    print("PARITY OK" if summary["ok"] else "PARITY MISMATCH")

    if args.json:
        args.json.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"\nWrote machine-readable report to {args.json}")

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
