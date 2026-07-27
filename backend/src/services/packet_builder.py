"""Unified packet builder. Called by every tile's /generate endpoint.

Per `phases/source/PHASE_23_packet_builder.md`:
- Generates 3 PDFs per packet: cover sheet, manual-upload walkthrough, and
  a form-fields summary
- Persists packet metadata so the gated download + tracker endpoints can
  retrieve it (in-memory store; Supabase mirror is best-effort)
- Returns `PacketResult(packet_id, fee_usd, file_count, zip_path, paid)`
"""
from __future__ import annotations

import datetime
import logging
import uuid
import zipfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .county_router import get_county_details, get_filing_fee
from .pdfa_generator import render_html_to_pdfa
from .translation_layer import (
    get_instructions,
    get_template_path,
    get_walkthrough,
)

logger = logging.getLogger(__name__)

PacketType = Literal[
    "small_claims",
    "expungement",
    "landlord_deposit",
    "landlord_repairs",
    "landlord_eviction",
    "traffic",
]
Language = Literal["en", "es"]

# Resolve `<backend>/storage/packets/` from this file's __file__ so the
# path works in both the repo-root dev layout and the Railway production
# image (where rootDirectory=/backend collapses backend/ into /app/).
# parents[2] from backend/src/services/packet_builder.py = backend/  (dev)
# parents[2] from /app/src/services/packet_builder.py     = /app/    (prod)
_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage" / "packets"


class PacketRequest(BaseModel):
    packet_type: PacketType
    language: Language = "en"
    county: str
    user_id: str
    tile_data: dict[str, Any] = Field(default_factory=dict)


class PacketResult(BaseModel):
    packet_id: str
    fee_usd: float
    file_count: int
    zip_path: str
    paid: bool = False


# In-memory packet registry. Tests + dev runs without Supabase rely on this
# being the source of truth. When `DatabaseManager.client` is available we
# also write through to a `packets` table (best-effort; failure is logged
# but never raised — preserves test_phase_23 pass criteria on dev boxes).
_PACKETS: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_packet(packet_id: str) -> dict[str, Any] | None:
    return _PACKETS.get(packet_id)


def mark_packet_paid(packet_id: str) -> bool:
    pkt = _PACKETS.get(packet_id)
    if not pkt:
        return False
    pkt["status"] = "paid"
    pkt["paid_at"] = _now_iso()
    return True


def track_packet_filing(packet_id: str, confirmation_number: str) -> bool:
    pkt = _PACKETS.get(packet_id)
    if not pkt:
        return False
    pkt["confirmation_number"] = confirmation_number
    pkt["filed_at"] = _now_iso()
    return True


async def build_packet(req: PacketRequest) -> PacketResult:
    packet_id = str(uuid.uuid4())
    packet_dir = _STORAGE_ROOT / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)

    county_info = get_county_details(req.county)
    fee = get_filing_fee(req.county, req.packet_type, req.tile_data)
    instructions = get_instructions(req.packet_type, req.language, req.county)
    walkthrough_steps = get_walkthrough(req.language)

    ctx = {
        **req.tile_data,
        "tile_data": req.tile_data,
        "county": county_info,
        "county_name": county_info.get("name", req.county),
        "instructions": instructions,
        "walkthrough": walkthrough_steps,
        "fee_usd": fee,
        "packet_id": packet_id,
        "packet_type": req.packet_type,
        "language": req.language,
    }

    cover_template = get_template_path(req.packet_type, req.language)
    cover = packet_dir / "01_cover_sheet.pdf"
    await render_html_to_pdfa(cover_template, ctx, cover)

    walkthrough_template = f"walkthroughs/manual_upload_{req.language}.html"
    walkthrough = packet_dir / "02_how_to_file.pdf"
    await render_html_to_pdfa(walkthrough_template, ctx, walkthrough)

    summary = packet_dir / "03_form_fields_summary.pdf"
    await render_html_to_pdfa(
        "cover_sheets/_form_fields_summary.html", ctx, summary
    )

    zip_path = packet_dir / f"legalclear_packet_{packet_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in [cover, walkthrough, summary]:
            zf.write(f, arcname=f.name)

    row = {
        "id": packet_id,
        "user_id": req.user_id,
        "packet_type": req.packet_type,
        "language": req.language,
        "county": req.county,
        "fee_usd": fee,
        "zip_path": str(zip_path),
        "status": "pending_payment",
        "confirmation_number": None,
        "filed_at": None,
        "created_at": _now_iso(),
    }
    _PACKETS[packet_id] = row

    # Best-effort Supabase mirror. The `packets` table is added by the
    # Phase 23 migration in `backend/migrations/2026_05_15_packets.sql`;
    # if the table is missing in this environment we still want builds
    # to succeed — local tests rely on in-memory state only.
    try:
        from src.memory.db import DatabaseManager  # noqa: WPS433

        dbm = DatabaseManager()
        if dbm.client is not None:
            dbm.client.table("packets").insert(row).execute()
    except Exception as exc:  # pragma: no cover — non-fatal mirror
        logger.debug(f"Supabase packets mirror skipped: {exc}")

    return PacketResult(
        packet_id=packet_id,
        fee_usd=fee,
        file_count=3,
        zip_path=str(zip_path),
        paid=False,
    )
