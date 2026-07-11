"""Packet endpoints — Phase 23.

Source: phases/source/PHASE_23_packet_builder.md.

Path note: source put this at backend/src/api/routes/packet.py; repo
location is backend/src/api/routers/ (Phase 10 divergence). HTTP paths
unchanged: /api/packet/build, /api/packet/{id}, /api/packet/{id}/download,
/api/packet/{id}/track.

Stripe checkout creation happens here (NOT in stripe_client.py) per the
source spec — the existing Phase 09 client handles the existing $5/$10/$15
+ subscription tiers; this router attaches the new $35 Filing Packet via
the same SDK without modifying Phase 09 internals.
"""
import logging
from pathlib import Path

import stripe
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.core.config import settings
from src.core.upl import apply_disclaimer
from src.services.packet_builder import (
    PacketRequest,
    build_packet,
    get_packet,
    mark_packet_paid,
    track_packet_filing,
)
from src.services.translation_layer import get_walkthrough

router = APIRouter(prefix="/api/packet")
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
PACKET_PRICE_CENTS = 3500  # $35.00 — "LegalClear Filing Packet"

# Success/cancel URLs default to the production domain but can be overridden
# via env vars (Railway preview deploys, local dev with VITE on :5173, etc.).
_FRONTEND = settings.FRONTEND_URL


async def build_packet_with_checkout(req: PacketRequest) -> dict:
    """Shared helper: build the packet, then either create a Stripe
    checkout session (PAYMENTS_ENABLED=true) or mark it paid and skip
    checkout (PAYMENTS_ENABLED=false — features free while off).

    Both /api/packet/build (this router) and the tile-generate endpoints
    in small_claims.py / expungement.py / landlord.py / traffic.py call
    this. Keeps the Stripe call in exactly one place.
    """
    result = await build_packet(req)

    if settings.PAYMENTS_ENABLED:
        checkout_url = _create_checkout(result, req)
    else:
        # Payments off — unlock the packet immediately, free of charge.
        mark_packet_paid(result.packet_id)
        checkout_url = ""

    return apply_disclaimer({
        "packet_id": result.packet_id,
        "fee_usd": result.fee_usd,
        "file_count": result.file_count,
        "checkout_url": checkout_url,
    }, lang=req.language if req.language in ("en", "es") else "en")


def _create_checkout(result, req: PacketRequest) -> str:
    """Create the $35 Stripe checkout session for a packet. Returns the
    checkout URL, or "" if creation fails (error logged). Faithful to the
    original Phase 23 implementation (see git history)."""
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": (
                                f"LegalClear Filing Packet ({req.packet_type})"
                            ),
                        },
                        "unit_amount": PACKET_PRICE_CENTS,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "packet_id": result.packet_id,
                "user_id": req.user_id,
                "packet_type": req.packet_type,
            },
            success_url=(
                f"{_FRONTEND}/filing-packet/{result.packet_id}?paid=1"
            ),
            cancel_url=(
                f"{_FRONTEND}/filing-packet/{result.packet_id}?paid=0"
            ),
        )
        return checkout.url
    except Exception as exc:
        logger.error(f"Stripe checkout creation failed: {exc}")
        return ""


@router.post("/build")
async def build(req: PacketRequest):
    return await build_packet_with_checkout(req)


# Static GET routes must precede the catch-all /{packet_id} route below
# so they don't get swallowed as packet_id values.
@router.get("/walkthrough")
async def walkthrough(lang: str = "en"):
    """Return the manual-upload walkthrough JSON used by the FilingPacket
    page. Same content as the PDF version that lands in the packet ZIP."""
    if lang not in ("en", "es"):
        lang = "en"
    return get_walkthrough(lang)


@router.get("/{packet_id}/download")
async def download_packet(packet_id: str):
    pkt = get_packet(packet_id)
    if not pkt:
        raise HTTPException(404, "Packet not found")
    if pkt.get("status") != "paid":
        raise HTTPException(402, "Payment required")
    zip_path = Path(pkt["zip_path"])
    if not zip_path.exists():
        raise HTTPException(500, "Packet file missing")
    return FileResponse(
        zip_path,
        filename=f"legalclear_packet_{packet_id}.zip",
        media_type="application/zip",
    )


@router.get("/{packet_id}")
async def get_packet_metadata(packet_id: str):
    pkt = get_packet(packet_id)
    if not pkt:
        raise HTTPException(404, "Packet not found")
    return pkt


@router.post("/{packet_id}/track")
async def track_filing(packet_id: str, confirmation_number: str):
    if not get_packet(packet_id):
        raise HTTPException(404, "Packet not found")
    track_packet_filing(packet_id, confirmation_number)
    return {
        "status": "tracked",
        "packet_id": packet_id,
        "confirmation_number": confirmation_number,
    }


@router.post("/{packet_id}/mark_paid")
async def mark_paid_dev(packet_id: str):
    """Dev-only convenience endpoint used by the FilingPacket page after
    Stripe redirects back with `?paid=1`. The Stripe webhook in
    `routes.py` is still the production path; this endpoint exists so
    local/manual flows can test the download gate without webhook
    plumbing. Safe to call multiple times — idempotent.
    """
    if not mark_packet_paid(packet_id):
        raise HTTPException(404, "Packet not found")
    return {"status": "paid", "packet_id": packet_id}
