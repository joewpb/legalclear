# TASK: B4d — deterministic URL output filter at the agent output boundary.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4d-url-filter (already checked out).

## Decision 4 (verbatim intent)
Strip every URL from generated agent output at the boundary. Log each stripped URL
with the agent name so emission rates are visible. No allowlist — the rule is no
external links, enforced deterministically (AGENTS.md: LLMs generate, deterministic
code guarantees). Proven necessary: B4b-1a showed prompt edits cannot stop models
emitting URLs from training data (clsmf.org, myflcourtaccess.com, invented domains).

## Job
1. Implement a deterministic URL/bare-domain stripper as a shared utility (suggest
   backend/src/core/url_filter.py). It must strip:
   - full URLs (http://, https://, www.)
   - bare domains in text (clsmf.org, myflcourtaccess.com — a conservative pattern:
     letters/digits with at least one dot and a valid-ish TLD, NOT matching statute
     cites like "Fla. Stat.", case cites, "§ 83.60(2)", "U.S.", "a.m.", "p.m.",
     "e.g.", "i.e.", "vs.", initials like "J. Smith", decimals, or version numbers)
   - mid-sentence occurrences, leaving the surrounding text readable (e.g.
     "Free help: floridalawhelp.org." → "Free help: ." is NOT acceptable — prefer
     "Free help:" or a coherent sentence). Report the chosen replacement strategy
     and show before/after examples for the known emitters.
2. Wire it on EVERY agent output path at the boundary — not per-agent opt-in. Find
   the common output assembly points (agent modules stream chunks; routers forward).
   The cleanest single choke point may be in the shared streaming/response helper —
   if one does not exist, wire the filter into each agent's final output assembly
   (document each site). Do NOT filter the prompt side (only generated OUTPUT).
3. Logging: every strip logs agent name, the stripped value, and ±60 chars of
   surrounding context at WARNING level (rate visible per agent).
4. Do not break the typed disclaimer events or any frame structure — the filter runs
   on text content, not SSE framing.

## Tests (red→green, required cases)
- clsmf.org and myflcourtaccess.com stripped (known emitters)
- a hallucinated domain (e.g. "floridalegalhelpdesk.org") stripped
- URL mid-sentence: surrounding words preserved, output readable
- False-positive guards: "Fla. Stat. § 83.60(2)", a case cite like "Smith v. Jones,
  123 So. 3d 456 (Fla. 2020)", "a.m.", "U.S. Constitution", decimals, "e.g." — NONE
  stripped
- Logging assertion: one test captures the log record with agent name + stripped value
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline on main is 275/1 — must not drop.

## Rules
- uv only. Backend only. No migrations, no secrets.
- Report: the utility's pattern + replacement strategy, before/after examples for the
  known emitters, every wiring site (file:line), test evidence, suite count.
