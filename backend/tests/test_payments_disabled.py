"""Decision 1 (DECISIONS.md) — PAYMENTS_ENABLED off by default, no route
payment-gated while it is off.

Asserts:
  1. The flag defaults to false when PAYMENTS_ENABLED is unset in the env.
  2. Every gate keyed on PAYMENTS_ENABLED (check_access, webhook, subscribe,
     florida-filing free-tier cap, packet checkout, chat expert paywall)
     is open while the flag is off — no payment-gated path is reachable.

These are unit/TestClient tests only — no Stripe network calls, no
Supabase creds required.
"""
import asyncio
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from src.api import routes
from src.api.routers import packet as packet_router
from src.agents import chat_expert
from src.core.config import settings
from src.payments import check_access

client = TestClient(routes.app)


def test_flag_defaults_to_off(monkeypatch):
    """With no PAYMENTS_ENABLED in the env, Settings() must resolve to False."""
    monkeypatch.delenv("PAYMENTS_ENABLED", raising=False)
    import src.core.config as config_module

    importlib.reload(config_module)
    try:
        assert config_module.settings.PAYMENTS_ENABLED is False
    finally:
        importlib.reload(config_module)


def test_check_access_free_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", False)
    # Even a user with no subscription and no free use left is allowed.
    result = check_access({"subscription_status": "free", "free_doc_used": True})
    assert result["allowed"] is True
    assert result["payment_type"] == "free"


def test_webhook_ignored_when_disabled(monkeypatch):
    monkeypatch.setattr(routes.settings, "PAYMENTS_ENABLED", False)
    r = client.post("/webhook", content=b"{}", headers={"stripe-signature": "bogus"})
    assert r.status_code == 200
    assert r.json() == {"status": "ignored", "reason": "payments_disabled"}


def test_subscribe_returns_free_when_disabled(monkeypatch):
    monkeypatch.setattr(routes.settings, "PAYMENTS_ENABLED", False)
    r = client.post(
        "/subscribe/user-123",
        params={
            "email": "a@example.com",
            "success_url": "https://x/success",
            "cancel_url": "https://x/cancel",
        },
        headers={"x-api-key": settings.API_KEY},
    )
    assert r.status_code == 200
    assert r.json() == {"checkout_url": "", "payments_enabled": False}


def test_florida_filing_not_gated_when_disabled(monkeypatch):
    monkeypatch.setattr(routes.settings, "PAYMENTS_ENABLED", False)
    monkeypatch.setattr(routes.db, "count_filings", lambda user_id: 99)
    monkeypatch.setattr(
        routes.db, "record_filing", lambda *a, **k: None
    )
    r = client.post(
        "/florida-filing/prepare",
        json={"county": "Miami-Dade", "document_id": "doc-1"},
        headers={"x-api-key": settings.API_KEY, "user-id": "user-1"},
    )
    # No 402 even though filing_count (99) would exceed the free-tier cap.
    assert r.status_code != 402
    assert r.status_code == 200


def test_packet_checkout_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(packet_router.settings, "PAYMENTS_ENABLED", False)

    class _FakeResult:
        packet_id = "pkt-1"
        fee_usd = 35.0
        file_count = 3

    async def _fake_build_packet(req):
        return _FakeResult()

    marked = {}

    def _fake_mark_packet_paid(packet_id):
        marked["packet_id"] = packet_id
        return True

    def _fail_create_checkout(*a, **k):
        raise AssertionError("Stripe checkout must not be created while payments are off")

    monkeypatch.setattr(packet_router, "build_packet", _fake_build_packet)
    monkeypatch.setattr(packet_router, "mark_packet_paid", _fake_mark_packet_paid)
    monkeypatch.setattr(packet_router, "_create_checkout", _fail_create_checkout)

    req = packet_router.PacketRequest(
        packet_type="small_claims", county="Miami-Dade", user_id="user-1"
    )
    result = asyncio.run(packet_router.build_packet_with_checkout(req))

    assert result["checkout_url"] == ""
    assert marked["packet_id"] == "pkt-1"


def test_chat_expert_paywall_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(chat_expert.settings, "PAYMENTS_ENABLED", False)
    agent = chat_expert.ChatExpertAgent.__new__(chat_expert.ChatExpertAgent)

    async def _collect_first_event():
        gen = chat_expert.ChatExpertAgent.chat(
            agent,
            module="not-a-real-module",  # fails fast, before any Anthropic call
            message="hello",
            session_id="s1",
            message_count=chat_expert.MAX_FREE_MESSAGES + 10,
        )
        return await gen.__anext__()

    first_event = asyncio.run(_collect_first_event())
    assert '"paywall": true' not in first_event
    assert "Unknown module" in first_event
