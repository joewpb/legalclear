"""EN/ES template + instructions lookup. Pre-translated, no live LLM call.

Per `phases/source/PHASE_23_packet_builder.md`:
- `instructions_{en,es}.json` lives at `backend/src/data/`
- Spanish entries must use U.S. court interpreter register (no MT tone)
- County-level overrides may shadow the per-packet-type base entry
"""
import json
from functools import lru_cache
from pathlib import Path

# parents[3] from backend/src/services/translation_layer.py = repo root
_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=2)
def _load_instructions(language: str) -> dict:
    path = _DATA_DIR / f"instructions_{language}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=2)
def _load_walkthrough_steps(language: str) -> dict:
    path = _DATA_DIR / f"walkthrough_steps_{language}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_template_path(packet_type: str, language: str) -> str:
    """Jinja2 path relative to backend/src/templates/."""
    return f"cover_sheets/{packet_type}_{language}.html"


def get_instructions(packet_type: str, language: str, county: str) -> dict:
    inst = _load_instructions(language)
    base = inst.get(packet_type, {})
    overrides = base.get("county_overrides", {}).get(county, {})
    return {**base, **overrides}


def get_walkthrough(language: str) -> dict:
    return _load_walkthrough_steps(language)
