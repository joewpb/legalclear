"""County-specific clerk info + filing fee tiers.

Source: phases/source/PHASE_23_packet_builder.md.

Reads all 67 FL counties from `backend/src/data/fl_county_clerk_details.json`.
`get_county_details()` falls back to a generic flclerks.com record when the
county is unknown (e.g., user typed a non-FL county string).
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "fl_county_clerk_details.json"
)


@lru_cache(maxsize=1)
def _load_counties() -> dict[str, dict[str, Any]]:
    with open(_DATA_FILE, encoding="utf-8") as f:
        return {c["name"]: c for c in json.load(f)}


def get_county_details(county_name: str) -> dict[str, Any]:
    counties = _load_counties()
    if county_name in counties:
        return counties[county_name]
    return {
        "name": county_name,
        "clerk_url": "https://www.flclerks.com/",
        "clerk_address": "",
        "clerk_phone": "(555) 000-0000",
        "fee_tier_1": 55,
        "fee_tier_2": 80,
        "fee_tier_3": 175,
        "fee_tier_4": 300,
    }


def get_filing_fee(county: str, packet_type: str, tile_data: dict) -> float:
    c = get_county_details(county)
    if packet_type == "small_claims":
        try:
            a = float(tile_data.get("amount", 0))
        except (TypeError, ValueError):
            a = 0.0
        if a <= 100:
            return float(c["fee_tier_1"])
        if a <= 500:
            return float(c["fee_tier_2"])
        if a <= 2500:
            return float(c["fee_tier_3"])
        return float(c["fee_tier_4"])
    if packet_type == "expungement":
        return 75.0
    if packet_type.startswith("landlord_"):
        return 401.0
    if packet_type == "traffic":
        return 90.0
    return 100.0
