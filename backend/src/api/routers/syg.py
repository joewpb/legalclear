"""Stand Your Ground analysis endpoint — Phase 6.

POST /api/syg/analyze {"text": "..."} -> fact terms, matched cases, and an
educational Stand Your Ground analysis with attorney-accountability
questions. Two LLM calls per submission; deterministic ranking in between.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.routers.case_law import _search_opinions_corpus, _tokenize
from src.services.syg_synthesis import analyze_syg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/syg", tags=["syg"])


class SygRequest(BaseModel):
    text: str


@router.post("/analyze")
async def analyze_syg_endpoint(payload: SygRequest) -> dict:
    """Educational SYG analysis grounded in matched Florida opinions.

    Never raises: extraction, search, and synthesis each fail soft.
    """
    text = (payload.text or "").strip()
    try:
        return analyze_syg(
            text=text,
            search_fn=_search_opinions_corpus,
            tokenizer=_tokenize,
        )
    except Exception:
        logger.exception("SYG analyze endpoint failed")
        from src.services.syg_synthesis import DISCLAIMER, SYG_STATUTES
        return {
            "terms": [],
            "cases": [],
            "analysis": {
                "title": "Analysis unavailable",
                "summary": "The analysis could not be completed for this "
                           "document. Below is the statutory framework.",
                "elements": SYG_STATUTES,
                "cases": [],
                "attorney_questions": [],
                "degraded": True,
            },
            "disclaimer": DISCLAIMER,
        }
