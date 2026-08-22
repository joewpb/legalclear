"""K3 — conditional framing (AGENTS 2c/2d) across wills_trusts,
property_casualty (first-party), and chat_expert system prompts.

Pure prompt-assertion tests: no live LLM calls. Asserts conditional/
consequence constructions are present and bare directive language is
absent, plus the citation-ownership constraints from the K3 dispatch
(Fla. Prob. R. 5.x is owned and citable; ch. 732/733/736 and § 627.x
are not owned and must not be cited).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents import chat_expert
from src.agents import property_casualty
from src.agents import wills_trusts

BARE_DIRECTIVES = ("you should", "you must", "you need to")

_CONDITIONAL_RE = re.compile(r"\bif\b", re.IGNORECASE)


def _assert_no_bare_directives(text: str) -> None:
    # Prompts legitimately instruct the model to avoid these phrases (e.g.
    # "No 'you should' / 'you must'") — strip those meta-instructions before
    # checking that the phrase isn't used as an actual directive.
    scrubbed = re.sub(r"['‘]you (should|must|need to)['’]", "", text, flags=re.IGNORECASE)
    lowered = scrubbed.lower()
    for phrase in BARE_DIRECTIVES:
        assert phrase not in lowered, f"bare directive {phrase!r} found"


def _assert_conditional_framing(text: str) -> None:
    assert _CONDITIONAL_RE.search(text), "no conditional ('if ...') construction found"


# ---------------------------------------------------------------------------
# wills_trusts.py
# ---------------------------------------------------------------------------


def test_wills_trusts_prompt_has_conditional_framing():
    _assert_conditional_framing(wills_trusts.SYSTEM_PROMPT)
    _assert_no_bare_directives(wills_trusts.SYSTEM_PROMPT)


def test_wills_trusts_prompt_cites_owned_probate_rules():
    assert "Fla. Prob. R." in wills_trusts.SYSTEM_PROMPT


def test_wills_trusts_prompt_does_not_cite_unowned_statutes():
    text = wills_trusts.SYSTEM_PROMPT
    for unowned in ("732.", "733.", "736.", "FL Statute 732", "FL Statute 736"):
        assert unowned not in text, f"unowned statute citation {unowned!r} found"


def test_wills_trusts_prompt_develops_both_administration_branches():
    text = wills_trusts.SYSTEM_PROMPT.lower()
    assert "administration is opened" in text or "administration is never opened" in text
    assert "reasonable" in text  # inaction-is-reasonable branch present


# ---------------------------------------------------------------------------
# property_casualty.py — first-party prompt only (bad_faith/premises frozen)
# ---------------------------------------------------------------------------


def test_property_casualty_first_party_prompt_has_conditional_framing():
    _assert_conditional_framing(property_casualty._FIRST_PARTY_SYSTEM_PROMPT)
    _assert_no_bare_directives(property_casualty._FIRST_PARTY_SYSTEM_PROMPT)


def test_property_casualty_first_party_prompt_cites_from_curated_set_only():
    """Dispatch I-1 replaced the K3 'cite nothing' instruction with a
    cite-from-the-P&C-curated-set instruction — the prompt now references
    the curated chapters/sections by name, but only ever the curated ones."""
    text = property_casualty._FIRST_PARTY_SYSTEM_PROMPT
    assert "curated set" in text
    assert "Never cite outside the owned corpus" in text


def test_property_casualty_first_party_prompt_develops_non_pursuit_branch():
    text = property_casualty._FIRST_PARTY_SYSTEM_PROMPT.lower()
    assert "may not be worthwhile" in text or "not worthwhile" in text


def test_property_casualty_frozen_prompt_untouched():
    """bad_faith/premises prompt is explicitly out of scope for K3."""
    text = property_casualty._BAD_FAITH_PREMISES_SYSTEM_PROMPT
    assert "624.155" in text
    assert "768.0755" not in text  # never was cited here; premises has no statute cite in this prompt


def test_property_casualty_deadline_payload_fields_untouched():
    """Deterministic key_deadlines schema/consumption is unchanged by prompt edits."""
    assert "governing_rule" in property_casualty._FIRST_PARTY_SYSTEM_PROMPT
    assert "computation_trace" in property_casualty._FIRST_PARTY_SYSTEM_PROMPT
    # I-3a: the module no longer hardcodes the clock list — the deadline keys
    # are derived from RULES via pc_rule_keys_for_regime. The mechanism, not
    # a frozen 5-key list, is the invariant.
    from deadline.rules import RULES, pc_rule_keys_for_regime
    assert set(pc_rule_keys_for_regime(None)) == {
        key for key in RULES if key.startswith("pc_")
    }


# ---------------------------------------------------------------------------
# chat_expert.py
# ---------------------------------------------------------------------------


def test_chat_expert_all_modules_present():
    assert set(chat_expert.SYSTEM_PROMPTS) == chat_expert.VALID_MODULES


def test_chat_expert_all_modules_have_conditional_framing():
    for module, prompt in chat_expert.SYSTEM_PROMPTS.items():
        _assert_conditional_framing(prompt)
        _assert_no_bare_directives(prompt)


def test_chat_expert_all_modules_keep_refusal_and_disclaimer_wiring():
    for module, prompt in chat_expert.SYSTEM_PROMPTS.items():
        assert "respond exactly" in prompt, f"{module}: off-topic refusal missing"
        assert "disclaimer" in prompt.lower(), f"{module}: disclaimer instruction missing"


def test_chat_expert_modules_develop_inaction_reasonable_branch():
    # small_claims, property_casualty, and wills_trusts explicitly call out
    # scenarios where not acting is the reasonable choice (Decision 13 / 2d).
    for module in ("small_claims", "property_casualty", "wills_trusts"):
        assert "reasonable" in chat_expert.SYSTEM_PROMPTS[module].lower()


def test_chat_prompt_carries_owned_citation_rule():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/agents/chat_expert.py").read_text()
    assert "_SHARED_CITATION_RULE" in src
    assert "2.514" in src
    assert "Fla. R. Crim. P. 3.x" in src
    assert "SYSTEM_PROMPTS[module] + _SHARED_CITATION_RULE" in src
