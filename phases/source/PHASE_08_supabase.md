# PHASE 08 — Supabase Production DB
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- Migrated from local SQLite to Supabase Postgres
- Tables: `users`, `sessions`, `documents`, `chats`, `usage_stats`, `system_log`
- Connection via `SUPABASE_URL` and `SUPABASE_KEY` env vars
- `get_db()` from Phase 01 now routes to Supabase in production

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
grep -E "supabase" backend/src/memory/db.py && echo "supabase wired ok"
grep -E "SUPABASE_URL|SUPABASE_KEY" backend/.env && echo "supabase env ok"
uv pip list | grep -i supabase && echo "supabase package ok"
```

## Contract provided to later phases

- All DB access through `get_db()` from Phase 01 — same interface, different backend.
- **Phase 23 will ADD a `packets` table** with this exact schema (do not rebuild — Phase 23 handles the migration itself):
  ```sql
  CREATE TABLE IF NOT EXISTS packets (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      packet_type TEXT NOT NULL,
      language TEXT NOT NULL,
      county TEXT NOT NULL,
      fee_usd REAL NOT NULL,
      zip_path TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending_payment',
      confirmation_number TEXT,
      filed_at TEXT,
      created_at TEXT NOT NULL
  );
  ```

## What to do if verification fails

STOP. Without Supabase, Phase 23 packet tracking won't persist.

## Final line

```
PHASE 08 VERIFIED — proceed to PHASE 09
```
