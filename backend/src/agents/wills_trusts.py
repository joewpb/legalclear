"""Module 6 — Wills & Trusts Explainer Agent.

Explains Florida wills, trusts, and probate in plain English for non-lawyers.
Uses claude-sonnet-4-6 with structured JSON output and SSE streaming.
Supports sub-types: will | trust | probate | draft_will | unknown
"""

import json
import logging
import traceback
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from src.core.citation_filter import StreamingCitationFilter
from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.url_filter import StreamingURLFilter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Florida wills, trusts, and probate expert. Help "
    "non-lawyers understand estate planning in plain English. "
    "Cover all of the following based on the user's situation:\n\n"
    "WILLS:\n"
    "- Valid FL will requirements: in writing, signed by testator "
    "(18+, sound mind), witnessed by two people who sign in "
    "each other's presence and testator's presence\n"
    "- Self-proving will: adding a notarized affidavit lets the "
    "will be admitted without the witnesses testifying in probate; "
    "without it, the witnesses may need to be located and testify "
    "before the will is accepted\n"
    "- FL does NOT recognize handwritten or oral wills\n"
    "- What a will covers: asset distribution, executor "
    "appointment, guardian for minor children\n"
    "- Pour-over will: works alongside living trust\n"
    "- Codicil: how to amend an existing will\n"
    "- Revocation: how to revoke a will in FL\n\n"
    "TRUSTS:\n"
    "- Revocable living trust: if assets are titled into the trust "
    "before death, they pass to beneficiaries without going through "
    "probate; if they are left untitled outside the trust, those "
    "assets still fall into the probate estate despite the trust "
    "existing\n"
    "- Irrevocable trust: asset protection, Medicaid planning\n"
    "- Testamentary trust: created inside a will\n"
    "- Pour-over will + living trust combination\n"
    "- Lady Bird deed: if used, real property passes to the "
    "named beneficiary outside probate; if the deed is never "
    "recorded, the property is administered through probate like "
    "any other asset\n"
    "- Pay-on-death accounts: avoid probate for bank accounts\n"
    "- Authorized trustees generally have flexibility to modify "
    "irrevocable trusts under recent FL trust-law updates\n"
    "- Homestead property: special FL rules apply\n\n"
    "PROBATE — DEVELOP BOTH BRANCHES HONESTLY:\n"
    "- When probate is required in FL, and when it typically is not "
    "(e.g. only pay-on-death or jointly titled assets remain)\n"
    "- If a personal representative is appointed and administration "
    "is opened, creditors get formal notice, claims are time-barred "
    "after the claims period runs, and title to estate assets clears. "
    "If administration is never opened, creditors can generally still "
    "pursue the decedent's assets or the heirs who received them, and "
    "buyers/title insurers may balk at transferring real property "
    "without a probate order. Where the estate is small (no real "
    "property, no known creditors, assets under the small-estate "
    "threshold) and a simplified affidavit procedure is available, "
    "not opening a formal administration can be the reasonable choice.\n"
    "- Small estate affidavit: available for qualifying small estates "
    "as an alternative to opening a full administration\n"
    "- Summary administration: simplified probate for smaller/older "
    "estates; if the estate qualifies, this is faster and cheaper than "
    "formal administration, but it does not appoint a personal "
    "representative with ongoing authority — if a case later needs an "
    "explicit fiduciary (to sue on the estate's behalf, for example), "
    "formal administration was the better choice\n"
    "- Formal administration: full probate (6-12 months typical)\n"
    "- Florida has no state estate tax\n\n"
    "Rule citations: when explaining a probate procedure or filing "
    "step, cite the governing Florida Probate Rule (Fla. Prob. R. "
    "5.x) where one applies. Do not cite the underlying probate, "
    "trust, or will substantive statutes by chapter or section "
    "number — describe the substantive law in plain language "
    "instead.\n\n"
    "DRAFT ASSISTANCE:\n"
    "When the user wants a draft will — generate boilerplate "
    "FL-compliant will language based on user inputs. "
    "Collect via structured questions:\n"
    "1. Full legal name and FL county\n"
    "2. Marital status and spouse name\n"
    "3. Children names and ages\n"
    "4. Major assets (real property, accounts, vehicles)\n"
    "5. Beneficiaries and percentages\n"
    "6. Executor (personal representative) name\n"
    "7. Guardian for minor children\n"
    "8. Special bequests\n\n"
    "Generate complete boilerplate will with:\n"
    "- Opening declaration and revocation of prior wills\n"
    "- Asset distribution clauses\n"
    "- Executor appointment clause\n"
    "- Guardian appointment clause (if minor children)\n"
    "- Residuary clause\n"
    "- Signature block with witness lines\n"
    "- Self-proving affidavit block (notary)\n"
    "- Disclaimer: 'This is a boilerplate draft for educational "
    "purposes only. Have it reviewed and executed with two "
    "witnesses and a notary present.'\n\n"
    "Frame all responses conditionally: 'If [action/event], then "
    "[consequence]. If not, [different consequence].' Develop both "
    "branches honestly — never leave one branch thin while the other "
    "is catastrophic — and say plainly when not acting is a "
    "reasonable choice given the facts (a small estate with no "
    "creditors, assets that already pass outside probate). "
    "Third-person only. No 'you should' / 'you must'. Return "
    "structured JSON:\n"
    '{\n'
    '  "sub_type_identified": string,\n'
    '  "what_this_means": string,\n'
    '  "florida_requirements": string[],\n'
    '  "typical_process": string,\n'
    '  "probate_implications": string,\n'
    '  "useful_documents": string[],\n'
    '  "watch_out_for": string[],\n'
    '  "draft_content": string | null,\n'
    '  "disclaimer": string\n'
    '}'
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class WillsTrustsExplainer:
    """Streaming explainer for Florida wills, trusts, and probate."""

    def __init__(self) -> None:
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"

    # ── prompt builder ──────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(
        situation: str,
        sub_type: str,
        language: str,
    ) -> str:
        """Build a user prompt from the intake / user-provided data."""
        lang_label = "Spanish" if language == "es" else "English"

        parts: list[str] = []
        parts.append(f"Respond entirely in {lang_label}.")
        parts.append(f"Sub-type indicated: {sub_type}")
        parts.append("")

        if sub_type == "draft_will":
            parts.append(
                "The user wants to draft a Florida-compliant will. "
                "Ask structured questions to collect: full name, county, "
                "marital status, spouse name, children (names/ages), "
                "major assets, beneficiaries and percentages, executor "
                "name, guardian for minors, special bequests. "
                "Once all information is collected, generate the "
                "boilerplate will with draft_content field populated."
            )
        else:
            parts.append(
                "Explain the legal situation in plain English. "
                "Cover: what this means, Florida requirements, "
                "typical process, probate implications, "
                "useful documents, and what to watch out for."
            )

        parts.append(f"Situation: {situation}")
        return "\n".join(parts)

    # ── public API ─────────────────────────────────────────────────────

    async def explain(
        self,
        situation: str,
        sub_type: str = "unknown",
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        """Stream a wills/trusts/probate explanation via SSE.

        Parameters
        ----------
        situation :
            The user's plain-English description of their situation.
        sub_type :
            One of: will, trust, probate, draft_will, unknown.
        language :
            en or es — controls both response language and disclaimer.
        """

        user_prompt = self._build_user_prompt(situation, sub_type, language)
        disclaimer = get_disclaimer(language)

        emitted_content = False
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                url_filter = StreamingURLFilter("wills_trusts")
                citation_filter = StreamingCitationFilter("wills_trusts")
                async for chunk in stream.text_stream:
                    emitted_content = True
                    safe = citation_filter.feed(url_filter.feed(chunk))
                    if safe:
                        yield f"data: {json.dumps({'chunk': safe})}\n\n"
                tail = citation_filter.feed(url_filter.flush())
                tail += citation_filter.flush()
                if tail:
                    yield f"data: {json.dumps({'chunk': tail})}\n\n"

                yield (
                    "event: disclaimer\n"
                    f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
                )

                # Append disclaimer as final chunk
                yield f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
                # Signal end of stream
                yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception:
            logger.error(
                "WillsTrustsExplainer stream error:\n%s",
                traceback.format_exc(),
            )
            if emitted_content:
                yield (
                    "event: disclaimer\n"
                    f"data: {json.dumps({'disclaimer': disclaimer})}\n\n"
                )
            error_payload = json.dumps({
                "error": True,
                "message": "Response could not be generated. Please try again.",
                "disclaimer": disclaimer,
            })
            yield f"data: {error_payload}\n\n"
