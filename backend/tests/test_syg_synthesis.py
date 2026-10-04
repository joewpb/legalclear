"""Phase 6 SYG synthesis — unit tests.

Covers the full parse ladder (Decision 20): clean parse = 1 call, garbage
recover = exactly 2 calls, double-garbage = degrade + marker; plus pipeline
behavior with injected search/LLM fakes. No real LLM calls, no DB.
"""
import asyncio
import json
import sys

sys.path.insert(0, "/home/hermes/workspace/legalclear/backend")

from src.api.routers.syg import SygRequest, analyze_syg_endpoint
from src.services import syg_synthesis as ss

DOC_A = "I was attacked by two men in a bar parking lot. I backed away "
DOC_A += "but they followed me. I had no way to retreat so I defended "
DOC_A += "myself with my hands. Police charged me with battery."

DOC_B = "Someone broke through my front door at 3am. I believed they "
DOC_B += "meant to hurt my family. I used force to stop them inside my "
DOC_B += "home. Police are investigating."


class FakeCall:
    """Scripted LLM: returns queued raw responses; raises when exhausted."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, prompt: str) -> str | None:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("FakeCall exhausted")
        return self.responses.pop(0)


def fake_search(term: str, court_filter: str, limit: int) -> list[dict]:
    return [{
        "cluster_id": 1000 + hash(term) % 999,
        "case_name": f"State v. {term.title().replace(' ', '')}",
        "citation": f"{abs(hash(term)) % 999} So. 2d 1",
        "court": "Fla.",
        "date_filed": "2020-01-15",
        "summary_plain": f"Decision about {term}.",
        "cite_count": 5,
    }]


def test_extract_clean_single_call():
    call = FakeCall([
        json.dumps({
            "terms": ["self-defense", "duty to retreat"],
            "facts": ["Two attackers", "Backed away"],
            "charges": ["battery"],
        }),
    ])
    terms, facts, charges = ss.extract_fact_terms(DOC_A, llm_call=call)
    assert terms == ["self-defense", "duty to retreat"]
    assert facts == ["Two attackers", "Backed away"]
    assert charges == ["battery"]
    assert call.calls == 1  # no retry burned


def test_extract_garbage_then_recover_two_calls():
    call = FakeCall([
        "Sure! Here is your analysis of the document. It was about "
        "self-defense and duty to retreat.",
        json.dumps({
            "terms": ["self-defense", "disparity of force"],
            "facts": [],
            "charges": [],
        }),
    ])
    terms, _, _ = ss.extract_fact_terms(DOC_A, llm_call=call)
    assert terms == ["self-defense", "disparity of force"]
    assert call.calls == 2  # exactly one tightened retry


def test_extract_double_garbage_degrades(caplog):
    call = FakeCall(["not json at all", "still not json"])
    terms, facts, charges = ss.extract_fact_terms(
        DOC_A, llm_call=call, tokenizer=lambda t: ["fallback", "term"],
    )
    assert terms == ["fallback", "term"]
    assert facts == [] and charges == []
    assert call.calls == 2
    assert any(
        "LLM_PARSE_DEGRADE" in r.message and "syg_fact_terms" in r.message
        for r in caplog.records
    )


def test_synthesize_degrades_to_statutes_no_fabrication(caplog):
    call = FakeCall(["garbage", "more garbage"])
    out = ss.synthesize(["Two attackers"], [], llm_call=call)
    assert out.get("degraded") is True
    assert "776.012" in " ".join(out["elements"])
    assert out["cases"] == []  # no invented case analysis
    assert out["attorney_questions"]


def test_synthesize_clean_grounded():
    cases = [{
        "case_name": "Dennis v. State",
        "citation": "51 So. 3d 456",
        "court": "Fla. Sup. Ct.",
        "date_filed": "2010-10-07",
        "summary_plain": "SYG immunity burden of proof at pretrial hearing.",
        "cluster_id": 123,
    }]
    resp = json.dumps({
        "title": "What Stand Your Ground could mean here",
        "summary": "If the facts show lawful presence, the statute frames "
                   "the analysis.",
        "elements": ["Who was the initial aggressor?"],
        "cases": [{
            "case_name": "Dennis v. State",
            "citation": "51 So. 3d 456",
            "why_it_matters": "It decided the burden of proof at the "
                              "immunity hearing.",
        }],
        "attorney_questions": ["Ask about immunity hearing burden."],
    })
    out = ss.synthesize(["Two attackers"], cases, llm_call=FakeCall([resp]))
    assert out["title"]
    assert out["cases"][0]["case_name"] == "Dennis v. State"
    assert out["attorney_questions"]


def test_pipeline_two_documents_differ():
    def echoing_call(prompt: str) -> str:
        # return terms that differ by document content
        terms = (["bar fight", "multiple attackers", "self-defense"]
                 if "bar parking" in prompt
                 else ["forcible entry", "home protection", "self-defense"])
        return json.dumps({"terms": terms, "facts": [], "charges": []})

    out_a = ss.analyze_syg(DOC_A, search_fn=fake_search, llm_call=echoing_call)
    out_b = ss.analyze_syg(DOC_B, search_fn=fake_search, llm_call=echoing_call)
    assert out_a["terms"] != out_b["terms"]
    assert out_a["terms"] == ["bar fight", "multiple attackers", "self-defense"]
    assert out_b["terms"] == ["forcible entry", "home protection", "self-defense"]
    assert out_a["cases"] and out_b["cases"]
    assert out_a["disclaimer"]


def test_cited_cases_exist_in_search_results():
    def echoing_call(prompt: str) -> str:
        return json.dumps({"terms": ["self-defense"], "facts": [], "charges": []})

    out = ss.analyze_syg(DOC_A, search_fn=fake_search, llm_call=echoing_call)
    cited_names = {c["case_name"] for c in out["analysis"].get("cases", [])}
    searched_names = {c["case_name"] for c in out["cases"]}
    assert cited_names <= searched_names or cited_names == set()


def test_empty_text_safe():
    out = ss.analyze_syg("   ", search_fn=fake_search, llm_call=None)
    assert out["terms"] == []
    assert "No document provided" in out["analysis"]["title"]


def test_empty_analysis_cases_fall_back_to_matched():
    def echoing_call(prompt: str) -> str:
        return json.dumps({
            "title": "T", "summary": "S",
            "elements": [], "cases": [], "attorney_questions": [],
        })

    out = ss.analyze_syg(DOC_A, search_fn=fake_search, llm_call=echoing_call)
    assert out["cases"]  # matched cases exist
    assert out["analysis"]["cases"]  # fallback populated, not vanished
    cited = {c["case_name"] for c in out["analysis"]["cases"]}
    matched = {c["case_name"] for c in out["cases"]}
    assert cited <= matched


def test_endpoint_passes_through(monkeypatch):
    captured = {}

    def stub_analyze(text, search_fn=None, tokenizer=None):
        captured["text"] = text
        return {"terms": ["x"], "cases": [], "analysis": {}, "disclaimer": "d"}

    monkeypatch.setattr(
        "src.api.routers.syg.analyze_syg", stub_analyze,
    )
    result = asyncio.run(analyze_syg_endpoint(SygRequest(text="hello")))
    assert captured["text"] == "hello"
    assert result["terms"] == ["x"]


def test_search_failure_fails_soft(caplog):
    def broken_search(term, cf, limit):
        raise RuntimeError("db down")

    def echoing_call(prompt: str) -> str:
        return json.dumps({"terms": ["self-defense"], "facts": [], "charges": []})

    out = ss.analyze_syg(DOC_A, search_fn=broken_search, llm_call=echoing_call)
    assert out["cases"] == []  # analysis still produced
    assert out["terms"] == ["self-defense"]
