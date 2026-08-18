"""Doctrine 2c/2d — conditional framing over directives in system prompts.

Pure string assertions against the SYSTEM_PROMPT constants. No LLM calls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.criminal_procedure import SYSTEM_PROMPT as CRIMINAL_PROMPT
from src.agents.discovery_motion import SYSTEM_PROMPT as DISCOVERY_PROMPT

# Bare directive phrasing the doctrine forbids ("you must file", "you should
# appear") — distinct from "Never state what someone should do", which is a
# guardrail sentence, not a directive itself.
_BARE_DIRECTIVES = (
    "you must",
    "you should",
    "you need to",
    "file this",
    "you have to",
)


def _assert_conditional(prompt: str) -> None:
    lowered = prompt.lower()
    assert "if you" in lowered or "if the" in lowered or "if they" in lowered
    for phrase in _BARE_DIRECTIVES:
        assert phrase not in lowered, f"found bare directive {phrase!r}"


def test_criminal_procedure_prompt_is_conditional():
    _assert_conditional(CRIMINAL_PROMPT)


def test_criminal_procedure_prompt_cites_owned_rules():
    for rule in ("3.130", "3.160", "3.170", "3.220"):
        assert rule in CRIMINAL_PROMPT


def test_criminal_procedure_prompt_does_not_soften_nonappearance():
    lowered = CRIMINAL_PROMPT.lower()
    assert "bench warrant" in lowered
    assert "should always appear" in lowered


def test_discovery_motion_prompt_is_conditional():
    _assert_conditional(DISCOVERY_PROMPT)


def test_discovery_motion_prompt_cites_owned_rules():
    assert "1.280" in DISCOVERY_PROMPT
    assert "1.400" in DISCOVERY_PROMPT
    assert "1.380" in DISCOVERY_PROMPT


def test_discovery_motion_prompt_develops_nonresponse_branch():
    lowered = DISCOVERY_PROMPT.lower()
    assert "sanctions" in lowered
    assert "waiver" in lowered
