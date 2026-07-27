"""
Orin opinion retrieval — Phase 9+.

Queries the 443K Florida court opinions stored on the Orin AGX (Jetson)
via SSH-tunneled psql. Complements the Supabase legal_opinions table
(700 opinions with precomputed summaries) with raw search results.

The Orin database has no precomputed situation_tags — search is via
plain_text full-text match against derived keywords.

Architecture:
  - SSH tunnel: localhost:5433 → Orin:5432  (managed externally)
  - psql invoked via subprocess (avoids asyncpg auth issues)
  - Results mapped to RelevantOpinion format (types.ts)
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Tag → keyword mapping ────────────────────────────────────────────────────
# Maps situation_tag values to plain_text search terms.
# Lowercase only; OR'd within each tag group.

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

# Simpler fallback: words from the tag itself
_TAG_WORDS = re.compile(r"[a-z_]+")


def _tag_to_search(tag: str) -> str:
    """Convert a situation_tag to a PostgreSQL tsquery-compatible search string."""
    keywords = TAG_KEYWORDS.get(tag)
    if keywords:
        return keywords
    # Fallback: use the tag name with underscores replaced by spaces
    return tag.replace("_", " ")


def _build_tsquery(tags: list[str]) -> str:
    """Build a tsquery string from situation_tags."""
    terms = []
    for tag in tags:
        search = _tag_to_search(tag)
        # Convert "word AND word OR word" to tsquery syntax
        # PostgreSQL tsquery uses & for AND, | for OR
        ts = search.replace(" AND ", " & ").replace(" OR ", " | ")
        terms.append(f"({ts})")
    return " | ".join(terms) if terms else ""


# ── Metadata extraction from plain_text ───────────────────────────────────────

# Florida appellate opinion header patterns
_RE_CASE_NAME = re.compile(
    r"^\s+(?:No\.\s*\S+\s+)?\s*"
    r"([A-Z][A-Za-z\s\'\-]+),\s*\n\s*(?:Appellant|Appellee|Petitioner|Respondent)",
    re.MULTILINE,
)
_RE_DOCKET = re.compile(r"No\.\s*([\dA-Z]+\-[\d]+)", re.MULTILINE)
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


def _extract_metadata(text: str) -> dict[str, str | None]:
    """Extract case_name, citation, court, date from opinion plain_text header."""
    header = text[:600]

    # Case name: try "X vs Y" pattern first
    case_name = None
    vs_match = re.search(r"^\s+([A-Z][A-Za-z\s\'\-]+),\s*\n\s+(?:Appellant|Petitioner)", header, re.MULTILINE)
    if vs_match:
        case_name = vs_match.group(1).strip()

    if not case_name:
        vs_match2 = re.search(
            r"^\s+([A-Z][A-Za-z\s\'\-]+)\s+(?:v\.|vs\.)\s+", header, re.MULTILINE,
        )
        if vs_match2:
            case_name = vs_match2.group(1).strip()

    if not case_name:
        # Fallback: first ALLCAPS name
        cap_match = re.search(r"^\s+([A-Z][A-Z\s\'\-]{5,}),", header, re.MULTILINE)
        if cap_match:
            case_name = cap_match.group(1).strip()

    # Docket/citation
    citation = None
    dock_match = _RE_DOCKET.search(header)
    if dock_match:
        citation = dock_match.group(1)

    # Court
    court = None
    court_match = _RE_COURT.search(header)
    if court_match:
        court = court_match.group(0)

    # Date
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


def _summarize(text: str, max_chars: int = 300) -> str:
    """Create a plain-English summary by extracting the first substantive paragraph."""
    lines = text.split("\n")
    # Skip header lines (court name, docket, etc.)
    body_start = 0
    for i, line in enumerate(lines):
        if len(line.strip()) > 80 and not line.strip().startswith(("No.", "Lower", "Opinion", "Not final")):
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
    host: str = "127.0.0.1",
    port: int = 5433,
    user: str = "joe",
    dbname: str = "legal_clear",
) -> list[dict]:
    """Search Orin opinions for situation_tags.

    Returns a list of dicts matching the RelevantOpinion TypeScript interface:
      {case_name, citation, court, date_filed, cite_count, outcome,
       summary_plain, summary_legal, attorney_prompt}

    On any error (tunnel down, psql not found, query timeout), returns [].
    """
    if not tags:
        return []

    tsquery = _build_tsquery(tags)
    if not tsquery:
        return []

    # Build ILIKE clauses from tags (no GIN index on 443K opinions)
    # Convert each tag to a search pattern: fourth_amendment → '%search%' OR '%seizure%' OR ...
    ilike_clauses = []
    for tag in tags:
        keywords = _tag_to_search(tag)
        # Extract individual words/patterns from the search string
        for word in re.split(r'\s+(?:OR|AND)\s+', keywords):
            word = word.strip().strip('"')
            if word and len(word) > 2:
                ilike_clauses.append(f"plain_text ILIKE '%{word}%'")

    if not ilike_clauses:
        return []

    where = " OR ".join(ilike_clauses[:8])  # limit to 8 clauses for performance

    sql = f"""
    COPY (
      SELECT opinion_id, plain_text, date_created
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
        )
        if result.returncode != 0:
            logger.warning("Orin psql failed (rc=%d): %s", result.returncode, result.stderr[:200])
            return []

        # Parse CSV output (handles multiline text properly)
        import csv as _csv, io as _io
        reader = _csv.reader(_io.StringIO(result.stdout))
        opinions = []
        for row in reader:
            if len(row) < 3:
                continue
            try:
                opinion_id = int(row[0])
                plain_text = row[1]
            except (ValueError, IndexError):
                continue
            meta = _extract_metadata(plain_text)
            summary = _summarize(plain_text)

            opinions.append({
                "case_name": meta["case_name"],
                "citation": meta["citation"],
                "court": meta["court"],
                "date_filed": meta["date_filed"],
                "cite_count": 0,           # Orin doesn't track cites
                "outcome": None,            # Would need extraction
                "summary_plain": summary,
                "summary_legal": summary[:200],
                "attorney_prompt": (
                    "Search and seizure issues in this case may be relevant "
                    "to your situation. Ask your attorney about this opinion."
                ),
                "_source": "orin",
                "_opinion_id": opinion_id,
            })

        return opinions[:limit]

    except subprocess.TimeoutExpired:
        logger.warning("Orin psql timed out")
        return []
    except FileNotFoundError:
        logger.warning("ssh not found — Orin opinions unavailable")
        return []
    except Exception:
        logger.error("Orin opinion search failed", exc_info=True)
        return []
