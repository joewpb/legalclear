#!/usr/bin/env python3
"""Dispatch G1 step 1: collect real citation-shaped phrasings emitted by
each prose surface, for building the regex from observed output rather than
imagination. One-shot script — not part of the test suite."""
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.pc_citations import PC_CURATED_CITATIONS  # noqa: E402
from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS  # noqa: E402
from src.agents.small_claims_citations import SMALL_CLAIMS_CURATED_CITATIONS  # noqa: E402
from src.core.citation_resolver import normalize_citation  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_surfaces import (  # noqa: E402
    run_agent,
)

CURATED = frozenset(
    set(SMALL_CLAIMS_CURATED_CITATIONS) | set(EVICTION_CURATED_CITATIONS) | set(PC_CURATED_CITATIONS)
)

# Generous collector: anything containing digit patterns near statute/rule
# words, so we don't miss unexpected phrasings.
COLLECTOR_RE = re.compile(
    r"[^.\n]{0,40}"
    r"(?:§|F\.?S\.?|Fla\.?\s*Stat|Florida\s+Statutes?|section|Fla\.?\s*Admin\.?\s*Code"
    r"|Florida\s+Administrative\s+Code|F\.A\.C\.|Fla\.?\s*R\.|R\.\s*Civ|R\.\s*Crim"
    r"|Sm\.\s*Cl\.|Prob\.\s*R\.|Gen\.\s*Prac)"
    r"[^.\n]{0,40}\d[\d.\-()]*[^.\n]{0,20}",
    re.IGNORECASE,
)

SURFACES = [
    ("explainer", "explainer"),
    ("small_claims", "small_claims"),
    ("criminal", "criminal"),
    ("discovery", "discovery"),
    ("wills_trusts", "wills_trusts"),
    ("property_casualty", "property_casualty"),
]

CHAT_MODULES = ["small_claims", "landlord_tenant"]


async def run_chat(module: str) -> str:
    from src.agents.chat_expert import ChatExpertAgent

    q = "I received a notice about my case. What statutes or rules apply and what are my deadlines?"
    chunks = []
    async for chunk in ChatExpertAgent().chat(module, q, f"collect-{module}", "en"):
        chunks.append(str(chunk))
    return " ".join(chunks)


def curated_or_not(phrasing: str) -> str:
    # best-effort classification only for the report — not authoritative
    digits = re.findall(r"\d+(?:\.\d+)*", phrasing)
    for d in digits:
        if normalize_citation(f"Fla. Stat. § {d}") in CURATED:
            return "curated"
    return "uncurated"


async def main():
    out_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "citation_phrasings.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    rows = []

    for name, kind in SURFACES:
        try:
            raw = await run_agent(kind)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: RUN FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        for m in COLLECTOR_RE.finditer(raw):
            phrasing = m.group(0).strip()
            key = (name, phrasing)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"surface": name, "phrasing": phrasing, "classification": curated_or_not(phrasing)})
            print(f"{name}: {phrasing!r}")

    for module in CHAT_MODULES:
        name = f"chat:{module}"
        try:
            raw = await run_chat(module)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: RUN FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        for m in COLLECTOR_RE.finditer(raw):
            phrasing = m.group(0).strip()
            key = (name, phrasing)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"surface": name, "phrasing": phrasing, "classification": curated_or_not(phrasing)})
            print(f"{name}: {phrasing!r}")

    with out_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"\nwrote {len(rows)} phrasings to {out_path}")


asyncio.run(main())
