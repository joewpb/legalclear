# LegalClear

Florida legal-information platform for self-represented (pro se) users.

## What it does

Users upload court documents. The platform classifies the document, extracts
deadlines with deterministic computation under Florida rules, explains it in
plain language, surfaces the relevant official court forms, and schedules
reminders before deadlines expire.

Additional tools: Small Claims wizard, Eviction defense, Traffic citation
wizard, Police Report Analyzer, FL Case Law Lookup, and a Filing Packet
builder.

## Status

- **v1 shipped 2026-05-15.** All 24 build phases complete and deployed to
  Railway. See `phases/LEDGER.md` for full v1 state.
- **v2 in progress.** Nine-phase build plan at `phases/BUILD_PLAN.md`.
  v2 adds a deadline engine, form catalog, statute corpus, evaluation harness,
  and a full UPL/escalation framework.

## Stack

| Layer    | Technology                                   |
|----------|----------------------------------------------|
| Backend  | Python / FastAPI — Railway (`zesty-delight`) |
| Frontend | React / TypeScript / Vite — Railway (`appealing-victory`) |
| Mobile   | Expo / React Native                          |
| Database | Supabase Postgres 17 (`miedifclpqewnixxkahs`, us-west-2) |
| Payments | Stripe                                       |
| Python   | `uv`                                         |

## Running locally

```bash
# Backend
cd backend
uv sync
uv run uvicorn src.api.routes:app --port 8001 --reload

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:3000
```

## Key docs

- `AGENTS.md` — build law; read by every agent operating in this repo
- `phases/BUILD_PLAN.md` — v2 phase sequence and Definitions of Done
- `phases/LEDGER.md` — v1 build state
- `backend/.env.example` — required environment variables (values are placeholders)

## Core principle

The product produces **legal information**, never **legal advice**. It
translates, surfaces options, and explains consequences. It never selects a
course of action for the user.
