# PHASE 06 — Risk Scanner Agent
**Status: ✅ Already built. VERIFY ONLY. Do NOT rebuild.**

## What this phase built

- `backend/src/agents/risk_scanner.py`
- Scans contracts and leases for RED / YELLOW / GREEN clauses
- Returns: `{clauses: [{text, severity, location, explanation, suggestion}]}`
- Severity values: `red | yellow | green`

## Universal rules

- uv only · backend on **8001** · Florida jurisdiction · Brutalist design tokens · `cache_control: ephemeral` · strip markdown fences from agent JSON · no `myflcourtaccess.com` automation.

## Verification commands

```bash
test -f backend/src/agents/risk_scanner.py && echo "risk_scanner present"
grep -E "def scan_risks|red|yellow|green" backend/src/agents/risk_scanner.py && echo "risk severity model ok"
```

## Contract provided to later phases

- Called by `/api/upload` for contracts and leases.
- Phase 21 Police Report Analyzer uses a SIMILAR severity model (high/medium/low) but is a separate agent.

## What to do if verification fails

STOP.

## Final line

```
PHASE 06 VERIFIED — proceed to PHASE 07
```
