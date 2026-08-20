"""K4 — landlord_tenant module wiring in chat_expert.py.

Pure prompt-assertion tests: no live LLM calls. Verifies the new
landlord_tenant module is registered, carries the required conditional
framing and no-date-arithmetic hard rule, and that the existing
unknown-module error path and shared citation rule still apply.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents import chat_expert


def test_landlord_tenant_in_valid_modules():
    assert "landlord_tenant" in chat_expert.VALID_MODULES
    assert "landlord_tenant" in chat_expert.SYSTEM_PROMPTS
    assert "landlord_tenant" in chat_expert.MODULE_LABELS


def test_landlord_tenant_prompt_cites_answer_clock_statute():
    prompt = chat_expert.SYSTEM_PROMPTS["landlord_tenant"]
    assert "83.60" in prompt


def test_landlord_tenant_prompt_has_conditional_framing_marker():
    prompt = chat_expert.SYSTEM_PROMPTS["landlord_tenant"].lower()
    assert " if " in prompt
    assert "reasonable" in prompt  # inaction-is-reasonable branch present


def test_landlord_tenant_prompt_forbids_date_arithmetic():
    prompt = chat_expert.SYSTEM_PROMPTS["landlord_tenant"].lower()
    assert "never compute" in prompt
    assert "date" in prompt


def test_landlord_tenant_prompt_has_refusal_and_disclaimer():
    prompt = chat_expert.SYSTEM_PROMPTS["landlord_tenant"]
    assert "respond exactly" in prompt
    assert "landlord-tenant law in florida" in prompt.lower()
    assert "disclaimer" in prompt.lower()


def test_unknown_module_still_returns_error_shape():
    async def _collect():
        chunks = []
        async for chunk in chat_expert.ChatExpertAgent().chat(
            module="not_a_real_module",
            message="hello",
            session_id="s1",
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(_collect())
    assert len(chunks) == 1
    payload = json.loads(chunks[0].removeprefix("data: ").strip())
    assert payload["error"] is True
    assert "Unknown module" in payload["message"]
    assert "disclaimer" in payload


def test_shared_citation_rule_applies_to_landlord_tenant():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "src/agents/chat_expert.py").read_text()
    assert "_SHARED_CITATION_RULE" in src
    assert "83.49, 83.56, 83.60" in src
    assert "SYSTEM_PROMPTS[module] + _SHARED_CITATION_RULE" in src
