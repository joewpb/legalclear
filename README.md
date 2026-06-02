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

| Layer      | Technology                                   |
|------------|----------------------------------------------|
| Backend    | Python / FastAPI — Railway (`zesty-delight`) |
| Frontend   | React / TypeScript / Vite — Railway (`appealing-victory`) |
| Mobile     | Expo / React Native                          |
| Database   | Supabase Postgres 17 (`miedifclpqewnixxkahs`, us-west-2) |
| Payments   | Stripe                                       |
| Compliance | `compliance/` — standalone governance framework |
| Python     | `uv`                                         |

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

# Compliance CLI
cd compliance
uv sync
uv run legalclear validate
uv run legalclear report --jurisdiction=eu_ai_act
uv run legalclear report --jurisdiction=florida_fdbr --format=pdf
```

## Key docs

- `AGENTS.md` — build law; read by every agent operating in this repo
- `phases/BUILD_PLAN.md` — v2 phase sequence and Definitions of Done
- `phases/LEDGER.md` — v1 build state
- `backend/.env.example` — required environment variables (values are placeholders)
- `compliance/controls/registry.yaml` — unified AI governance control registry

## Core principle

The product produces **legal information**, never **legal advice**. It
translates, surfaces options, and explains consequences. It never selects a
course of action for the user.

---

## AI Governance Compliance Framework

```
compliance/
├── controls/registry.yaml          # Source of truth — 49 controls, 9 categories
├── src/compliance/
│   ├── schemas/                    # Pydantic v2 models (Control, Registry, Evidence)
│   ├── jurisdictions/
│   │   ├── base.py                 # ProjectionBase — deterministic projection engine
│   │   ├── eu_ai_act/              # EU AI Act (OJ L 2024/1689) — strictest baseline
│   │   ├── nist_ai_rmf/            # NIST AI RMF (NIST AI 100-1, Jan 2023)
│   │   ├── colorado_caia/          # Colorado CAIA (C.R.S. §§ 6-1-1701–6-1-1711)
│   │   ├── california_admt/        # California ADMT (Cal. Code Regs. tit. 11, §§ 7020–7029)
│   │   └── florida_fdbr/           # Florida FDBR (Fla. Stat. §§ 501.171–501.1735)
│   ├── evidence/                   # Content-addressed artifact store (SHA-256)
│   ├── reports/                    # Markdown + PDF report generator
│   ├── api/                        # FastAPI router (/compliance/*)
│   └── cli.py                      # `legalclear` entry point (Typer)
└── tests/                          # 86 tests, 100% pass
```

### Jurisdiction Matrix

| Control Category     | EU AI Act | NIST RMF | CO CAIA | CA ADMT | FL FDBR |
|----------------------|:---------:|:--------:|:-------:|:-------:|:-------:|
| Data Governance      | ✓ (6)     | ✓        | ✓       | ✓       | ✓       |
| Transparency         | ✓ (7)     | ✓        | ✓       | ✓       | ✓       |
| Human Oversight      | ✓ (5)     | ✓        | ✓       | ✓       | ✓       |
| Risk Management      | ✓ (6)     | ✓        | ✓       | ✓       | ✓       |
| Technical Robustness | ✓ (5)     | ✓        | ✓       | ✓       | ✓       |
| Record Keeping       | ✓ (5)     | ✓        | ✓       | ✓       | ✓       |
| Accuracy & Bias      | ✓ (6)     | ✓        | ✓       | ✓       | ✓       |
| Security             | ✓ (5)     | ✓        | ✓       | ✓       | ✓       |
| Incident Response    | ✓ (4)     | ✓        | ✓       | ✓       | ✓       |

**Auto-satisfaction rule:** Any control satisfying EU AI Act automatically
satisfies all weaker jurisdictions that control maps to (deterministic
projection, not a copy). Exception: FL FDBR §501.1735 children's provisions
(CTRL-004) require independent Florida verification — no direct EU AI Act
equivalent.

### REST API

When the compliance package is installed, the backend exposes:

```
GET  /compliance/controls                    — all 49 controls
GET  /compliance/controls/{jurisdiction}     — jurisdiction projection
POST /compliance/evidence                    — submit artifact (base64)
GET  /compliance/reports/{jurisdiction}      — generate report (markdown/html)
```

### CLI quickstart

```bash
cd compliance && uv sync

# Validate registry
uv run legalclear validate

# Generate reports
uv run legalclear report --jurisdiction=eu_ai_act
uv run legalclear report --jurisdiction=florida_fdbr --format=pdf

# Inspect a jurisdiction
uv run legalclear project --jurisdiction=colorado_caia

# Manage evidence
uv run legalclear evidence list
uv run legalclear evidence submit path/to/model_card.md --controls CTRL-006,CTRL-013
uv run legalclear evidence refresh
```
