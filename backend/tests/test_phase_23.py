"""Phase 23 verification — verbatim from
phases/source/PHASE_23_packet_builder.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
  - STRIPE_SECRET_KEY env var set so /api/packet/build can mint a real
    Stripe checkout Session in test mode (sk_test_…)
  - Playwright chromium installed (already in cache from earlier phases)

Hardest assertion: test_no_mode_b. Any non-commented `myflcourtaccess`
reference under backend/src/ fails the build. The Phase 11 file
`backend/src/platforms/florida_courts.py` carries the required
`# walkthrough text only` marker; tile routers and packet services do
NOT reference the string at all.
"""
import httpx
import json
import os
import time
from pathlib import Path

BACKEND = "http://localhost:8001"


def test_packet_build():
    r = httpx.post(
        f"{BACKEND}/api/packet/build",
        json={
            "packet_type": "small_claims",
            "language": "en",
            "county": "Miami-Dade",
            "user_id": "test_001",
            "tile_data": {
                "claim_type": "Unpaid debt",
                "amount": 1500,
                "defendant_type": "Individual",
                "defendant_name": "X",
                "defendant_address": "Y",
            },
        },
        timeout=60.0,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert all(k in d for k in ["packet_id", "fee_usd", "checkout_url"])
    assert d["checkout_url"].startswith("https://checkout.stripe.com")
    return d["packet_id"]


def test_download_gated():
    pid = test_packet_build()
    r = httpx.get(f"{BACKEND}/api/packet/{pid}/download")
    assert r.status_code == 402


def test_zip_exists():
    pid = test_packet_build()
    time.sleep(2)
    d = Path(f"backend/storage/packets/{pid}")
    assert d.exists()
    for f in [
        "01_cover_sheet.pdf",
        "02_how_to_file.pdf",
        "03_form_fields_summary.pdf",
    ]:
        assert (d / f).exists()
    assert len(list(d.glob("*.zip"))) == 1


def test_pdfa_metadata():
    import pikepdf

    pid = test_packet_build()
    time.sleep(2)
    with pikepdf.open(
        Path(f"backend/storage/packets/{pid}/01_cover_sheet.pdf")
    ) as pdf:
        with pdf.open_metadata() as meta:
            assert meta.get("pdfaid:part") == "1"
            assert meta.get("pdfaid:conformance") == "B"


def test_spanish():
    r = httpx.post(
        f"{BACKEND}/api/packet/build",
        json={
            "packet_type": "small_claims",
            "language": "es",
            "county": "Miami-Dade",
            "user_id": "test_002",
            "tile_data": {
                "claim_type": "Unpaid debt",
                "amount": 500,
                "defendant_type": "Individual",
                "defendant_name": "Juan",
                "defendant_address": "Calle",
            },
        },
        timeout=60.0,
    )
    assert r.status_code == 200, r.text


def test_all_packet_types():
    types = [
        (
            "small_claims",
            {
                "claim_type": "Other",
                "amount": 100,
                "defendant_type": "Individual",
                "defendant_name": "X",
                "defendant_address": "Y",
            },
        ),
        (
            "expungement",
            {
                "disposition": "Dismissed",
                "charge": "Petit theft",
                "completed_terms": "Yes",
                "previously_sealed": "No",
                "years_since_closed": "5-10",
            },
        ),
        (
            "landlord_deposit",
            {
                "move_out_date": "2026-01-01",
                "deposit_amount": 1000,
                "current_address": "A",
                "landlord_name": "B",
                "landlord_address": "C",
            },
        ),
        (
            "landlord_repairs",
            {
                "property_address": "X",
                "issue_type": "AC",
                "issue_description": "B",
                "prior_communication": "E",
                "tenant_intent": "w",
            },
        ),
        (
            "landlord_eviction",
            {
                "eviction_type": "nonpayment",
                "notice_type": "3-day",
                "notice_date": "2026-04-01",
                "defenses": ["paid"],
            },
        ),
        (
            "traffic",
            {
                "citation_type": "Speeding",
                "citation_number": "X",
                "issue_date": "2026-04-15",
                "county": "Miami-Dade",
                "chosen_path": "contest",
            },
        ),
    ]
    for ptype, td in types:
        r = httpx.post(
            f"{BACKEND}/api/packet/build",
            json={
                "packet_type": ptype,
                "language": "en",
                "county": "Miami-Dade",
                "user_id": "test_003",
                "tile_data": td,
            },
            timeout=60.0,
        )
        assert r.status_code == 200, f"Failed: {ptype} — {r.text}"


def test_tracking():
    pid = test_packet_build()
    r = httpx.post(
        f"{BACKEND}/api/packet/{pid}/track",
        params={"confirmation_number": "MFC-2026-1234567"},
    )
    assert r.status_code == 200


def test_counties():
    with open("backend/src/data/fl_county_clerk_details.json") as f:
        c = json.load(f)
    assert len(c) == 67


def test_bilingual_instructions():
    en = json.load(open("backend/src/data/instructions_en.json"))
    es = json.load(open("backend/src/data/instructions_es.json"))
    needed = {
        "small_claims",
        "expungement",
        "landlord_deposit",
        "landlord_repairs",
        "landlord_eviction",
        "traffic",
    }
    assert needed.issubset(en.keys())
    assert needed.issubset(es.keys())


def test_no_mode_b():
    """CRITICAL: Confirm no Python file in backend/src navigates to myflcourtaccess."""
    for root, _, files in os.walk("backend/src"):
        for f in files:
            if f.endswith(".py"):
                content = Path(root, f).read_text().lower()
                if "myflcourtaccess" in content:
                    # Only allowed in clearly-marked walkthrough text comments
                    assert (
                        "# walkthrough text only" in content
                    ), f"Mode B leak detected in {root}/{f}"


if __name__ == "__main__":
    test_packet_build()
    test_download_gated()
    test_zip_exists()
    test_pdfa_metadata()
    test_spanish()
    test_all_packet_types()
    test_tracking()
    test_counties()
    test_bilingual_instructions()
    test_no_mode_b()
    print("PHASE 23 COMPLETE — all checks passed.")
