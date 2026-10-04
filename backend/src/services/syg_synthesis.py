"""Stand Your Ground analysis — Phase 6 synthesis layer.

Pipeline (deterministic spine, two LLM calls total per submission):

  document text
    -> 1 extraction call   -> weighted fact terms  (fail-soft: tokenize)
    -> term search          -> matched FL opinions  (deterministic ranking)
    -> 1 synthesis call     -> educational SYG analysis grounded in those
                               cases + attorney-accountability questions
                               (fail-soft: statutory framework only, no
                               invented case analysis)

UPL boundary: the output explains what the law says and what matched cases
decided — it never selects a course of action for the user. Every analysis
carries the attorney-confirmation disclaimer and questions to ask counsel.
"""
import logging

from src.core.config import settings
from src.core.json_utils import ladder_call_sync

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

# Public-law statutory skeleton used when the synthesis LLM degrades.
# Names/numbers only — the degrade path never fabricates case analysis.
SYG_STATUTES = [
    ("Fla. Stat. § 776.012 — use or threatened use of force in defense of "
     "person (no duty to retreat where not engaged in unlawful activity and "
     "attacked in a place the person has a right to be)"),
    ("Fla. Stat. § 776.013 — home protection; presumption of reasonable "
     "fear of death or great bodily harm for an unlawful, forcible entry"),
    ("Fla. Stat. § 776.032 — immunity from criminal prosecution and civil "
     "action for justifiable use of force"),
]

EXTRACTION_PROMPT = (
    "A person submitted a document (police report, incident narrative, or "
    "their account) and wants to understand how Florida's Stand Your Ground "
    "law could apply. Read the document below and extract:\n"
    "1. terms — the 4 to 8 most search-relevant legal concepts and factual "
    "phrases (e.g. 'self-defense', 'duty to retreat', 'disparity of force', "
    "'multiple attackers', 'forcible entry', 'justifiable use of force').\n"
    "2. facts — up to 5 one-line factual findings from the document, stated "
    "neutrally (what the document says happened; never conclusions about "
    "guilt, justification, or how the law applies).\n"
    "3. charges — any charges, offenses, or citations mentioned, or an "
    "empty list.\n"
    "Return ONLY a JSON object: "
    '{{"terms": [...], "facts": [...], "charges": [...]}}\n'
    "\nDOCUMENT:\n{text}"
)

SYNTHESIS_PROMPT = (
    "A person submitted a document and wants a PLAIN-LANGUAGE, educational "
    "explanation of how Florida's Stand Your Ground law (Fla. Stat. "
    "§§ 776.012, 776.013, 776.032) could apply to their situation. You are "
    "producing legal information, never legal advice.\n"
    "\nFacts extracted from their document:\n{facts}\n"
    "\nFlorida court opinions matched by term search:\n{cases}\n"
    "Write an educational analysis as a JSON object with:\n"
    '  "title": short plain-language title (e.g. "What Stand Your Ground '
    'could mean in your situation"),\n'
    '  "summary": 2-4 plain sentences explaining, in general terms, what '
    'Stand Your Ground addresses and which of its ideas may matter here, '
    'framed conditionally ("If the facts show X, then Y can follow"),\n'
    '  "elements": up to 6 short bullets, each one legal idea a court would '
    'examine (e.g. who was the initial aggressor, whether the person was '
    'lawfully present, whether force was proportional), phrased as '
    'questions or conditions, never as conclusions about THIS person,\n'
    '  "cases": for each matched case actually useful to the explanation: '
    '{{"case_name": ..., "citation": ..., "why_it_matters": one plain '
    'sentence stating what that case decided and why the idea matters '
    'here,}} (at most 5, never cite a case whose summary you were not '
    'given),\n'
    '  "attorney_questions": 3-5 specific questions the person should ask '
    'a Florida attorney, grounded in the facts and the matched cases.\n'
    "GROUNDING RULE (hard): base every statement about a case ONLY on the "
    "summary provided for that case. Never invent facts about a case, "
    "never claim a case involved facts not stated in its summary, and "
    "never assert the law applies to this person's situation — explain "
    "what the law requires and let the attorney questions carry the "
    "application. If no case is relevant, use only the statutes.\n"
    "Return ONLY the JSON object — no markdown, no prose around it."
)


def _call_anthropic(prompt: str) -> str | None:
    """One Anthropic call. Returns raw text or None (transport/HTTP failure)."""
    import requests as _requests

    key = settings.ANTHROPIC_API_KEY
    if not key:
        return None
    try:
        resp = _requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1200,
                "temperature": 0.3,
            },
            timeout=25,
        )
        if resp.status_code != 200:
            logger.warning("SYG LLM call returned HTTP %s", resp.status_code)
            return None
        return resp.json()["content"][0]["text"].strip()
    except Exception:
        logger.warning("SYG LLM call failed", exc_info=True)
        return None


def extract_fact_terms(
    text: str,
    llm_call=None,
    tokenizer=None,
) -> tuple[list[str], list[str], list[str]]:
    """1 LLM call -> (terms, facts, charges). Degrades deterministically to
    tokenized terms — the request always completes, never fabricates."""
    call = llm_call or _call_anthropic
    parsed, degraded = ladder_call_sync(
        call,
        EXTRACTION_PROMPT.format(text=text[:12000]),
        site="syg_fact_terms",
        expect="dict",
    )
    if degraded or not parsed:
        fallback_terms = tokenizer(text) if tokenizer else text.split()
        logger.warning("LLM_PARSE_DEGRADE site=syg_fact_terms reason=fallback")
        return list(fallback_terms)[:8], [], []
    terms = [t for t in parsed.get("terms", []) if isinstance(t, str)]
    facts = [f for f in parsed.get("facts", []) if isinstance(f, str)]
    charges = [c for c in parsed.get("charges", []) if isinstance(c, str)]
    if not terms:
        return list(tokenizer(text))[:8] if tokenizer else [], facts, charges
    return terms, facts, charges


def synthesize(
    facts: list[str],
    cases: list[dict],
    llm_call=None,
) -> dict:
    """1 LLM call -> structured analysis. Degrades to the statutory
    framework — never invents case analysis."""
    call = llm_call or _call_anthropic
    facts_txt = "\n".join(f"- {f}" for f in facts) or "(none extracted)"
    cases_txt = ""
    for i, op in enumerate(cases[:5]):
        cases_txt += (
            f"--- CASE {i} ---\n"
            f"Case: {op.get('case_name', '')}\n"
            f"Citation: {op.get('citation', 'Not available')}\n"
            f"Court: {op.get('court', '')}\n"
            f"Date: {op.get('date_filed', 'Not available')}\n"
            f"Summary: {str(op.get('summary_plain', ''))[:400]}\n\n"
        )
    if not cases_txt:
        cases_txt = "(no matched cases)"
    parsed, degraded = ladder_call_sync(
        call,
        SYNTHESIS_PROMPT.format(facts=facts_txt, cases=cases_txt),
        site="syg_synthesis",
        expect="dict",
    )
    if degraded or not parsed:
        logger.warning(
            "LLM_PARSE_DEGRADE site=syg_synthesis reason=fallback"
        )
        return {
            "title": "Florida Stand Your Ground law — the statutory framework",
            "summary": (
                "A plain-language analysis could not be generated for this "
                "document. Below is the statutory framework courts apply, "
                "plus the matched cases."
            ),
            "elements": SYG_STATUTES,
            "cases": [],
            "attorney_questions": [
                ("Ask a Florida attorney whether Stand Your Ground immunity "
                 "could apply to the facts in your document, and what a "
                 "pretrial immunity hearing would look like."),
            ],
            "degraded": True,
        }
    return parsed


def _dedupe_cases(rows: list[dict], max_cases: int = 8) -> list[dict]:
    seen: set[int] = set()
    out: list[dict] = []
    for r in rows:
        cid = r.get("cluster_id")
        if cid is None or cid in seen:
            continue
        seen.add(cid)
        out.append(r)
        if len(out) >= max_cases:
            break
    return out


DISCLAIMER = (
    "LegalClear provides legal information, not legal advice. This analysis "
    "explains how Florida's Stand Your Ground law is written and what "
    "matched cases decided — it does not tell you how to act. Confirm your "
    "situation with a Florida attorney. Free help: /find-legal-help."
)


def analyze_syg(
    text: str,
    search_fn,
    llm_call=None,
    tokenizer=None,
) -> dict:
    """Full pipeline. Never raises — every layer fails soft."""
    if not text or not text.strip():
        return {
            "terms": [],
            "cases": [],
            "analysis": {
                "title": "No document provided",
                "summary": "Submit a document or description to analyze.",
                "elements": SYG_STATUTES,
                "cases": [],
                "attorney_questions": [],
            },
            "disclaimer": DISCLAIMER,
        }
    terms, facts, charges = extract_fact_terms(text, llm_call, tokenizer)

    cases: list[dict] = []
    if search_fn is not None:
        try:
            for term in terms[:6]:
                cases.extend(search_fn(term, "all", 10) or [])
            cases = _dedupe_cases(cases)
        except Exception:
            logger.warning("SYG search failed; proceeding without cases",
                           exc_info=True)
            cases = []

    analysis = synthesize(facts, cases, llm_call)
    # the LLM may return "cases": [] even when cases were matched — an empty
    # analysis case list must fall back to the matched set, never vanish
    if not analysis.get("cases"):
        analysis["cases"] = [
            {
                "case_name": c.get("case_name", ""),
                "citation": c.get("citation", "Not available"),
                "court": c.get("court", ""),
                "date_filed": c.get("date_filed"),
            }
            for c in cases
        ]
    return {
        "terms": terms,
        "charges_mentioned": charges,
        "cases": cases,
        "analysis": analysis,
        "disclaimer": DISCLAIMER,
    }
