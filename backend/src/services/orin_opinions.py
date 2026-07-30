"""
Orin opinion retrieval — Phase 9+.

Queries the 443K Florida court opinions stored on the Orin AGX (Jetson)
via SSH-tunneled psql. Complements the Supabase legal_opinions table
(700 opinions with precomputed summaries) with raw search results.

Architecture:
  - No local port-forward is used. Each query SSHes into the Orin box
    (`ssh joe@100.117.93.67`) and runs `psql -U joe -d legal_clear`
    there over the Unix socket (peer auth). A localhost:5433 tunnel is
    NOT required and is not referenced by any code path.
  - psql invoked via subprocess (avoids asyncpg auth issues)
  - DeepSeek batch extraction for metadata (cheap, one API call per
    search); requires DEEPSEEK_API_KEY in the environment. Regex
    fallback (~60% accuracy) when the key is absent or the call fails.
"""

from __future__ import annotations

import csv as _csv
import io as _io
import json
import logging
import re
import subprocess
from dataclasses import dataclass

from src.core.config import settings

logger = logging.getLogger(__name__)

# ── Tag → keyword mapping ────────────────────────────────────────────────────

TAG_KEYWORDS: dict[str, str] = {
    "fourth_amendment": "search AND seizure OR fourth amendment OR warrantless OR probable cause OR reasonable suspicion",
    "fifth_amendment": "miranda OR self-incrimination OR fifth amendment OR custodial interrogation",
    "sixth_amendment": "right to counsel OR speedy trial OR confrontation OR sixth amendment",
    "traffic_stop": "traffic stop OR vehicle search OR DUI checkpoint OR pretextual stop",
    "arrest": "arrest OR probable cause OR warrantless arrest OR false arrest",
    "suppression": "motion to suppress OR exclusionary rule OR fruit of poisonous tree",
    "domestic_violence": "domestic violence OR battery OR injunction OR restraining order",
    "drug_possession": "possession of OR controlled substance OR trafficking OR constructive possession",
    "burglary": "burglary OR breaking and entering OR trespass",
    "theft": "theft OR larceny OR petit theft OR grand theft",
    "assault": "assault OR aggravated assault OR battery",
    "robbery": "robbery OR armed robbery OR carjacking",
    "homicide": "murder OR manslaughter OR homicide OR felony murder",
    "sexual_offense": "sexual battery OR lewd OR molestation OR sexual offense",
    "firearms": "firearm OR weapon OR gun OR concealed weapon",
    "sentencing": "sentencing OR downward departure OR habitual offender OR minimum mandatory",
    "appeal": "appeal OR direct appeal OR postconviction OR habeas",
    "juvenile": "juvenile OR delinquency OR minor",
    "evidence": "hearsay OR authentication OR chain of custody OR expert testimony",
    "confession": "confession OR admission OR statement against interest",
    "plea": "plea agreement OR plea bargain OR nolo contendere OR change of plea",
    "probation": "probation OR community control OR violation of probation",
    "stand_your_ground": "stand your ground OR self-defense OR immunity OR justifiable use",
    "discovery": "discovery OR brady OR giglio OR reciprocal discovery",
    "speedy_trial": "speedy trial OR rule 3.191 OR demand for speedy trial",
}


def _tag_to_search(tag: str) -> str:
    keywords = TAG_KEYWORDS.get(tag)
    if keywords:
        return keywords
    return tag.replace("_", " ")


def _build_tsquery(tags: list[str]) -> str:
    terms = []
    for tag in tags:
        search = _tag_to_search(tag)
        ts = search.replace(" AND ", " & ").replace(" OR ", " | ")
        terms.append(f"({ts})")
    return " | ".join(terms) if terms else ""


# ── Metadata extraction ───────────────────────────────────────────────────────

# Regex patterns for fallback
_RE_DOCKET = re.compile(r"No\.\s*([\dA-Z]+-[\d]+)", re.MULTILINE)
_RE_COURT = re.compile(
    r"(Supreme Court of Florida|District Court of Appeal|"
    r"Circuit Court|County Court)",
    re.MULTILINE,
)
_RE_DATE = re.compile(
    r"(?:Opinion filed|filed)\s+([A-Z][a-z]+ \d{1,2}, \d{4})", re.MULTILINE
)


@dataclass
class OrinOpinion:
    opinion_id: int
    case_name: str
    citation: str
    court: str
    date_filed: str | None
    summary_plain: str
    summary_legal: str


def _extract_metadata_regex(text: str) -> dict[str, str | None]:
    """Regex fallback for case metadata extraction."""
    header = text[:600]
    case_name = None

    vs_match = re.search(
        r"^\s+([A-Z][A-Za-z\s'\-]+),\s*\n\s*(?:Appellant|Petitioner)",
        header, re.MULTILINE,
    )
    if vs_match:
        case_name = vs_match.group(1).strip()

    if not case_name:
        vs_match2 = re.search(
            r"^\s+([A-Z][A-Za-z\s'\-]+)\s+(?:v\.|vs\.)\s+",
            header, re.MULTILINE,
        )
        if vs_match2:
            case_name = vs_match2.group(1).strip()

    if not case_name:
        cap_match = re.search(
            r"^\s+([A-Z][A-Z\s'\-]{5,}),", header, re.MULTILINE,
        )
        if cap_match:
            case_name = cap_match.group(1).strip()

    citation = None
    dock_match = _RE_DOCKET.search(header)
    if dock_match:
        citation = dock_match.group(1)

    court = None
    court_match = _RE_COURT.search(header)
    if court_match:
        court = court_match.group(0)

    date_filed = None
    date_match = _RE_DATE.search(header)
    if date_match:
        date_filed = date_match.group(1)

    return {
        "case_name": case_name or "Unknown Case",
        "citation": citation or "N/A",
        "court": court or "Florida Court",
        "date_filed": date_filed,
    }


def _batch_extract_metadata(opinions: list[dict]) -> list[dict]:
    """Extract metadata from multiple opinions in ONE DeepSeek call."""
    key = settings.DEEPSEEK_API_KEY
    if not key:
        for op in opinions:
            meta = _extract_metadata_regex(op["plain_text"])
            op.update(meta)
        return opinions

    # Build batch prompt from headers
    headers_text = ""
    for i, op in enumerate(opinions[:10]):
        headers_text += f"--- OPINION {i} ---\n{op['plain_text'][:600]}\n\n"

    try:
        import requests as _requests
        resp = _requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{
                    "role": "user",
                    "content": (
                        "For each opinion header (--- OPINION N ---), extract: "
                        "case_name, citation (docket), court, date_filed. "
                        "Return ONLY a JSON array, one object per opinion:\n"
                        '[{"case_name":"...","citation":"...",'
                        '"court":"...","date_filed":"..."}]\n\n'
                        f"{headers_text}"
                    ),
                }],
                "max_tokens": 800,
                "temperature": 0,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                for i, meta in enumerate(data):
                    if i < len(opinions) and isinstance(meta, dict):
                        opinions[i].update({
                            "case_name": str(meta.get("case_name", "Unknown Case")),
                            "citation": str(meta.get("citation", "N/A")),
                            "court": str(meta.get("court", "Florida Court")),
                            "date_filed": meta.get("date_filed"),
                        })
                return opinions
    except Exception:
        logger.warning("DeepSeek batch metadata extraction failed, falling back to regex", exc_info=True)

    # Fallback: regex
    for op in opinions:
        meta = _extract_metadata_regex(op["plain_text"])
        op.update(meta)
    return opinions


def _summarize(text: str, max_chars: int = 300) -> str:
    """First substantive paragraph as plain-English summary."""
    lines = text.split("\n")
    body_start = 0
    for i, line in enumerate(lines):
        if (len(line.strip()) > 80
                and not line.strip().startswith(("No.", "Lower", "Opinion", "Not final"))):
            body_start = i
            break
    body = " ".join(lines[body_start:body_start + 8]).strip()
    if len(body) > max_chars:
        body = body[:max_chars - 3] + "..."
    return body or text[:max_chars]


# ── Query ─────────────────────────────────────────────────────────────────────

def search_orin_opinions(
    tags: list[str],
    limit: int = 5,
) -> list[dict]:
    """Search Orin opinions for situation_tags.

    Returns list matching RelevantOpinion TypeScript interface.
    On any error returns [].
    """
    if not tags:
        return []

    tsquery = _build_tsquery(tags)
    if not tsquery:
        return []

    ilike_clauses = []
    for tag in tags:
        keywords = _tag_to_search(tag)
        for word in re.split(r"\s+(?:OR|AND)\s+", keywords):
            word = word.strip().strip('"')
            if word and len(word) > 2:
                ilike_clauses.append(f"plain_text ILIKE '%{word}%'")

    if not ilike_clauses:
        return []

    where = " OR ".join(ilike_clauses[:8])

    sql = f"""
    COPY (
      SELECT opinion_id, plain_text
      FROM opinions
      WHERE plain_text IS NOT NULL
        AND plain_text != ''
        AND ({where})
      ORDER BY date_created DESC
      LIMIT 50
    ) TO STDOUT WITH CSV;
    """

    try:
        result = subprocess.run(
            [
                "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                "joe@100.117.93.67",
                "psql -U joe -d legal_clear -t -A",
            ],
            input=sql,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("Orin psql failed (rc=%d): %s", result.returncode, result.stderr[:200])
            return []

        _csv.field_size_limit(10_000_000)
        reader = _csv.reader(_io.StringIO(result.stdout))
        raw_opinions = []
        for row in reader:
            if len(row) < 2:
                continue
            try:
                opinion_id = int(row[0])
                plain_text = row[1]
            except (ValueError, IndexError):
                continue
            summary = _summarize(plain_text)
            raw_opinions.append({
                "opinion_id": opinion_id,
                "plain_text": plain_text,
                "summary_plain": summary,
                "summary_legal": summary[:200],
            })

        # One DeepSeek call to extract metadata for all opinions
        enriched = _batch_extract_metadata(raw_opinions)

        results = []
        for op in enriched[:limit]:
            results.append({
                "case_name": op.get("case_name", "Unknown Case"),
                "citation": op.get("citation", "N/A"),
                "court": op.get("court", "Florida Court"),
                "date_filed": op.get("date_filed"),
                "cite_count": 0,
                "outcome": None,
                "summary_plain": op.get("summary_plain", ""),
                "summary_legal": op.get("summary_legal", ""),
                "attorney_prompt": (
                    "Relevant Florida case law. "
                    "Ask your attorney about this opinion."
                ),
                "_source": "orin",
                "_opinion_id": op.get("opinion_id"),
            })

        return results

    except subprocess.TimeoutExpired:
        logger.warning("Orin psql timed out")
        return []
    except FileNotFoundError:
        logger.warning("ssh not found — Orin opinions unavailable")
        return []
    except Exception:
        logger.exception("Orin opinion search failed")
        return []
