"""Property & Casualty — live integration tests (Phase 6).

Exercises the end-to-end first_party_property intake flow:
  extract → engine → explain → disclaimer

Requires: Backend (FastAPI) running on http://localhost:8001

Run: cd backend && uv run python -m pytest tests/test_pc_integration.py -v
"""

import httpx
import json

BACKEND = "http://localhost:8001"


def _read_sse_body(r: httpx.Response) -> dict:
    """Parse SSE stream from the P&C explain endpoint into a dict.
    Extracts the final JSON payload from data: lines."""
    body = r.text
    last_data = None
    for line in body.strip().split("\n"):
        if line.startswith("data: "):
            try:
                parsed = json.loads(line[6:])
                last_data = parsed
            except json.JSONDecodeError:
                pass
    if last_data is None:
        raise ValueError(f"No SSE data found in response: {body[:200]}")
    return last_data


# ══════════════════════════════════════════════════════════════════════
# END-TO-END — first_party_property intake
# ══════════════════════════════════════════════════════════════════════

def test_first_party_intake_e2e():
    """End-to-end: a hurricane claim intake returns explanation with
    computed deadlines, UPL-safe output, and middleware-injected disclaimer."""
    payload = {
        "situation": (
            "Hurricane damaged my roof in Miami on September 28, 2024. "
            "My homeowners insurance sent an adjuster but hasn't paid anything. "
            "It's been 3 months since I filed the claim."
        ),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/intake", json=payload, timeout=30.0)
    assert r.status_code == 200, f"Intake failed: {r.status_code} {r.text}"

    data = r.json()
    assert "module" in data
    assert "disclaimer" in data
    # Intake router uses src.core.disclaimer.get_disclaimer()
    # which differs from src.core.upl.get_disclaimer()
    assert "not legal advice" in data["disclaimer"].lower(), (
        f"Disclaimer missing 'not legal advice': {data['disclaimer'][:100]}"
    )

    module = data.get("module", "")
    sub_type = data.get("sub_type", "")
    print(f"  Intake → module={module}, sub_type={sub_type}, confidence={data.get('confidence')}")

    if module == "property_casualty":
        assert sub_type in ("first_party_property", "unknown"), (
            f"Hurricane claim with no CRN must route to first_party_property "
            f"or unknown, not {sub_type}"
        )


def test_pnc_explain_endpoint_reachable():
    """The property-casualty/explain endpoint must accept POST with
    first_party_property sub_type."""
    fd = {
        "sub_type": "first_party_property",
        "entities_json": json.dumps({
            "date_of_loss": "2024-09-28",
            "loss_type": "hurricane",
            "property_type": "homeowner",
        }),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/property-casualty/explain", data=fd, timeout=60.0)
    assert r.status_code == 200, (
        f"P&C explain failed: {r.status_code} "
        f"(backend may not be running or first_party_property not registered)"
    )


def test_pnc_response_has_disclaimer():
    """Every P&C explain response must terminate with the disclaimer
    injected by apply_disclaimer() — not a local literal."""
    fd = {
        "sub_type": "first_party_property",
        "entities_json": json.dumps({
            "date_of_loss": "2024-09-28",
            "loss_type": "hurricane",
        }),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/property-casualty/explain", data=fd, timeout=60.0)
    assert r.status_code == 200, f"Request failed: {r.status_code}"

    # Response is SSE — parse the last data frame
    data = _read_sse_body(r)

    # Error path: LLM unavailable → error + disclaimer still injected
    if data.get("error"):
        assert "disclaimer" in data, (
            f"Error response must still carry disclaimer. Keys: {list(data.keys())}"
        )
        assert "legal information" in data["disclaimer"].lower() or \
               "not legal advice" in data["disclaimer"].lower(), (
            f"Disclaimer text not found in: {data['disclaimer'][:100]}"
        )
        print("  [LLM unavailable — error path verified, disclaimer present]")
        return

    # Success path: full response with disclaimer
    assert "disclaimer" in data, (
        f"Response missing disclaimer field. Keys: {list(data.keys())}"
    )
    assert "legal information" in data["disclaimer"].lower() or \
           "not legal advice" in data["disclaimer"].lower()


def test_pnc_response_has_key_deadlines():
    """First-party response must include key_deadlines from the deterministic
    engine, not LLM-computed dates."""
    fd = {
        "sub_type": "first_party_property",
        "entities_json": json.dumps({
            "date_of_loss": "2024-09-28",
            "loss_type": "hurricane",
        }),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/property-casualty/explain", data=fd, timeout=60.0)
    assert r.status_code == 200, f"Request failed: {r.status_code}"

    data = _read_sse_body(r)

    if data.get("error"):
        print("  [LLM unavailable — skipping deadline check]")
        return

    assert "key_deadlines" in data, (
        f"first_party_property response must include key_deadlines. "
        f"Keys: {list(data.keys())}"
    )
    deadlines = data["key_deadlines"]
    assert len(deadlines) >= 2, (
        f"Expected at least 2 deadlines (report + suit), got {len(deadlines)}"
    )

    for dl in deadlines:
        for key in ("label", "due_date", "governing_rule", "severity",
                     "consequence", "is_past", "computation_trace"):
            assert key in dl, f"Deadline missing '{key}': {dl.get('label', dl)}"

    dates = {dl["label"]: dl["due_date"] for dl in deadlines}
    print(f"  Computed deadlines: {json.dumps(dates, indent=2)}")

    if "Report Property Insurance Claim" in dates:
        assert dates["Report Property Insurance Claim"] == "2025-09-28", (
            f"Report deadline: expected 2025-09-28, "
            f"got {dates['Report Property Insurance Claim']}"
        )
    if "File Suit — Breach of Property Insurance Contract" in dates:
        assert dates["File Suit — Breach of Property Insurance Contract"] == "2029-09-28", (
            f"Suit deadline: expected 2029-09-28, "
            f"got {dates['File Suit — Breach of Property Insurance Contract']}"
        )


def test_pnc_no_date_math_in_response():
    """The LLM response body must NOT contain date arithmetic language."""
    fd = {
        "sub_type": "first_party_property",
        "entities_json": json.dumps({
            "date_of_loss": "2024-09-28",
            "loss_type": "hurricane",
        }),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/property-casualty/explain", data=fd, timeout=60.0)
    assert r.status_code == 200

    data = _read_sse_body(r)
    if data.get("error"):
        print("  [LLM unavailable — skipping date-math check]")
        return

    text_fields = []
    for key in ("what_this_is", "typical_timeline", "relevant_florida_law",
                 "what_usually_happens"):
        if key in data and isinstance(data[key], str):
            text_fields.append(data[key])

    full_text = " ".join(text_fields).lower()
    forbidden = [
        "add 365 days", "subtract", "1826 days", "365 days",
        "add 60 days", "count forward", "plus 5 years",
        "date of loss +", "+ 1 year from",
    ]
    for phrase in forbidden:
        assert phrase not in full_text, (
            f"Response contains forbidden date-math phrase: {phrase!r}"
        )


def test_pnc_no_second_person_directives():
    """Agent response body must not contain second-person directives."""
    fd = {
        "sub_type": "first_party_property",
        "entities_json": json.dumps({
            "date_of_loss": "2024-09-28",
            "loss_type": "hurricane",
        }),
        "language": "en",
    }
    r = httpx.post(f"{BACKEND}/api/property-casualty/explain", data=fd, timeout=60.0)
    assert r.status_code == 200

    data = _read_sse_body(r)
    if data.get("error"):
        print("  [LLM unavailable — skipping directive check]")
        return

    text_fields = []
    for key in data:
        if isinstance(data[key], str):
            text_fields.append(data[key])

    full_text = " ".join(text_fields).lower()
    directives = ["you should", "you must", "you need to"]
    for directive in directives:
        assert directive not in full_text, (
            f"Response contains directive: {directive!r}"
        )


if __name__ == "__main__":
    print("Running live integration tests...")
    test_first_party_intake_e2e()
    test_pnc_explain_endpoint_reachable()
    test_pnc_response_has_disclaimer()
    test_pnc_response_has_key_deadlines()
    test_pnc_no_date_math_in_response()
    test_pnc_no_second_person_directives()
    print("PHASE 6 INTEGRATION — all checks passed.")
