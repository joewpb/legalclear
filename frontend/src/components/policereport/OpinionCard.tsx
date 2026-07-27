import { useState } from "react";
import { Scale, ChevronDown, BookOpen, UserCheck, Compass } from "lucide-react";
import type { RelevantOpinion } from "./types";

/**
 * OpinionCard — LegalClear
 *
 * Surfaces a single relevant court opinion anywhere on the platform that a
 * user's situation_tags match. Built for people with no legal background:
 * plain-English first, legal precision available on demand, and a dual-state
 * next step that works whether or not the person already has a lawyer.
 *
 * Data shape (one row from the Supabase `legal_opinions` table):
 *   case_name, citation, court, date_filed, cite_count,
 *   outcome, summary_plain, summary_legal, attorney_prompt
 */

const COURT_SHORT: Record<string, string> = {
  "Supreme Court of Florida": "Fla. Supreme Court",
  "District Court of Appeal of Florida": "Fla. District Court of Appeal",
};

// Localized strings. The card renders its own disclaimer because it is built
// to be embedded anywhere on the platform, not just under a page that already
// shows one. EN/ES to satisfy the CLAUDE.md invariant that every user-facing
// string honors `language`.
//
// The opinion CORPUS (summary_plain / summary_legal / attorney_prompt) is
// English-only today (ES corpus deferred — see SPEC_LEDGER). Rather than hide
// English case law from a Spanish reader, we render an honesty stamp so they
// know it exists and can get help reading it. EN has no stamp (no notice).
const STRINGS: Record<
  "en" | "es",
  { disclaimer: string; englishOnlyNotice: string }
> = {
  en: {
    disclaimer:
      "This is legal information, not legal advice. LegalClear is not a law firm and cannot tell you what to do in your case.",
    englishOnlyNotice: "", // EN path: corpus is English-native, no stamp.
  },
  es: {
    disclaimer:
      "Esta es información legal, no asesoría legal. LegalClear no es un bufete de abogados y no puede decirle qué hacer en su caso.",
    englishOnlyNotice:
      "La jurisprudencia está disponible únicamente en inglés por el momento.",
  },
};

type PlainBlock = { label: string | null; body: string };

function parsePlainSummary(text: string | null | undefined): PlainBlock[] {
  if (!text) return [];
  const labels = [
    "WHAT HAPPENED",
    "THE RULE",
    "WHAT THE COURT DECIDED",
    "WHY THIS MAY MATTER TO YOU",
  ];
  const blocks: PlainBlock[] = [];
  const pattern = new RegExp(
    `(${labels.join("|")}):\\s*([\\s\\S]*?)(?=(?:${labels.join("|")}):|$)`,
    "g"
  );
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    blocks.push({ label: match[1], body: match[2].trim() });
  }
  if (blocks.length === 0) blocks.push({ label: null, body: text.trim() });
  return blocks;
}

function formatYear(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const y = new Date(dateStr).getFullYear();
  return Number.isNaN(y) ? "" : String(y);
}

export default function OpinionCard({
  opinion,
  language = "en",
}: {
  opinion: RelevantOpinion;
  language?: "en" | "es";
}) {
  const [showLegal, setShowLegal] = useState(false);
  if (!opinion) return null;

  const {
    case_name, citation, court, date_filed, cite_count,
    outcome, summary_plain, summary_legal, attorney_prompt,
  } = opinion;

  const courtLabel = COURT_SHORT[court] || court;
  const year = formatYear(date_filed);
  const plainBlocks = parsePlainSummary(summary_plain);
  const t = STRINGS[language];

  return (
    <article className="oc">
      {/* Eyebrow: signals this is context, not advice */}
      <div className="oc-eyebrow">
        <Scale className="oc-eyebrow-icon" aria-hidden="true" />
        <span>What courts have said</span>
      </div>

      {/* ES honesty stamp: corpus is English-only. Rendered ABOVE the body so a
          Spanish reader sees the language gap before the English text. Default
          is STAMP (preserve information). To instead HIDE the whole card for ES
          readers, flip one boolean: `if (language === "es") return null;` here. */}
      {t.englishOnlyNotice && (
        <p className="oc-notice">{t.englishOnlyNotice}</p>
      )}

      {/* Case identity */}
      <header className="oc-head">
        <h3 className="oc-case">
          <span className="oc-case-name">{case_name}</span>
        </h3>
        <div className="oc-meta">
          {courtLabel && <span className="oc-court">{courtLabel}</span>}
          {year && <span className="oc-dot" aria-hidden="true">·</span>}
          {year && <span>{year}</span>}
          {citation && <span className="oc-dot" aria-hidden="true">·</span>}
          {citation && <span className="oc-cite">{citation}</span>}
          {cite_count > 0 && (
            <>
              <span className="oc-dot" aria-hidden="true">·</span>
              <span className="oc-meta-cite">cited {cite_count} times</span>
            </>
          )}
        </div>
      </header>

      {/* Plain-English breakdown — the primary content */}
      <div className="oc-plain">
        {plainBlocks.map((block, i) => {
          const isMatter = block.label === "WHY THIS MAY MATTER TO YOU";
          return (
            <div
              key={i}
              className={`oc-block${isMatter ? " oc-block-matter" : ""}`}
            >
              {block.label && (
                <div className="oc-block-label">
                  {isMatter && (
                    <Compass className="oc-block-icon" aria-hidden="true" />
                  )}
                  {block.label}
                </div>
              )}
              <p className="oc-block-body">{block.body}</p>
            </div>
          );
        })}
      </div>

      {/* Questions for your attorney — the accountability core */}
      <div className="oc-next">
        <div className="oc-next-col oc-next-questions">
          <div className="oc-next-head">
            <UserCheck className="oc-next-icon" aria-hidden="true" />
            Questions for your attorney
          </div>
          <p className="oc-next-body oc-attorney-question">
            {attorney_prompt}
          </p>
        </div>
        <div className="oc-next-col">
          <div className="oc-next-head">
            <Compass className="oc-next-icon" aria-hidden="true" />
            No attorney yet?
          </div>
          <p className="oc-next-body">
            Save this question. When you consult an attorney — many offer free
            first consultations — ask them this directly to understand your options.
          </p>
        </div>
      </div>

      {/* Legal detail — collapsed by default, for power users / attorneys */}
      {summary_legal && (
        <div className="oc-legal">
          <button
            className="oc-legal-toggle"
            onClick={() => setShowLegal((v) => !v)}
            aria-expanded={showLegal}
          >
            <BookOpen className="oc-legal-icon" aria-hidden="true" />
            <span>The legal detail</span>
            <ChevronDown
              className={`oc-chevron${showLegal ? " oc-chevron-open" : ""}`}
              aria-hidden="true"
            />
          </button>
          {showLegal && (
            <div className="oc-legal-body">
              <p>{summary_legal}</p>
              {outcome && (
                <p className="oc-outcome">
                  <span className="oc-outcome-label">Outcome</span>
                  {outcome}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Standing disclaimer — the UPL guardrail, always present */}
      <p className="oc-disclaimer">{t.disclaimer}</p>

      <style>{`
        .oc {
          --ink: #14261F;
          --ink-soft: #4A5D54;
          --paper: #FCFBF7;
          --line: #E4E0D4;
          --line-soft: #EEEBE1;
          --seal: #1E6B4E;
          --seal-wash: #EEF5F0;
          --amber: #B57314;
          --amber-wash: #FBF3E4;

          font-family: "Tiempos Text", Charter, Georgia, "Times New Roman", serif;
          color: var(--ink);
          background: var(--paper);
          border: 1px solid var(--line);
          border-radius: 3px;
          padding: 1.5rem 1.625rem 1.375rem;
          max-width: 640px;
          position: relative;
          line-height: 1.6;
        }
        .oc::before {
          content: "";
          position: absolute;
          top: -1px;
          bottom: -1px;
          left: 5px;
          width: 1px;
          background: var(--line);
        }

        .oc-eyebrow {
          display: flex;
          align-items: center;
          gap: 7px;
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.09em;
          text-transform: uppercase;
          color: var(--seal);
          margin-bottom: 0.875rem;
        }
        .oc-eyebrow-icon { width: 13px; height: 13px; stroke-width: 2; }

        .oc-notice {
          margin: 0 0 1rem;
          padding: 0.625rem 0.75rem;
          background: var(--amber-wash);
          border-left: 2px solid var(--amber);
          border-radius: 2px;
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 12.5px;
          line-height: 1.45;
          color: var(--ink-soft);
        }

        .oc-head { margin-bottom: 1.125rem; }
        .oc-case {
          margin: 0 0 0.375rem;
          font-size: 1.375rem;
          line-height: 1.25;
          font-weight: 600;
          letter-spacing: -0.01em;
        }
        .oc-case-name { font-style: italic; }
        .oc-meta {
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 12.5px;
          color: var(--ink-soft);
          display: flex;
          flex-wrap: wrap;
          align-items: baseline;
          gap: 6px;
        }
        .oc-dot { color: var(--line); }
        .oc-cite { font-variant-numeric: tabular-nums; }

        .oc-plain { display: flex; flex-direction: column; gap: 0.875rem; }
        .oc-block-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 10.5px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-soft);
          margin-bottom: 0.25rem;
        }
        .oc-block-icon { width: 12px; height: 12px; stroke-width: 2; color: var(--seal); }
        .oc-block-body { margin: 0; font-size: 15.5px; }

        .oc-block-matter {
          background: var(--seal-wash);
          border-radius: 3px;
          padding: 0.875rem 1rem;
          margin-top: 0.125rem;
        }
        .oc-block-matter .oc-block-label { color: var(--seal); }

        .oc-next {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1px;
          background: var(--line-soft);
          border: 1px solid var(--line-soft);
          border-radius: 3px;
          margin: 1.25rem 0 1.125rem;
          overflow: hidden;
        }
        .oc-next-col { background: var(--paper); padding: 0.875rem 1rem; }
        .oc-next-questions { background: var(--seal-wash); }
        .oc-next-head {
          display: flex;
          align-items: center;
          gap: 6px;
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.03em;
          color: var(--ink);
          margin-bottom: 0.375rem;
        }
        .oc-next-icon { width: 13px; height: 13px; stroke-width: 2; color: var(--seal); }
        .oc-next-body {
          margin: 0;
          font-size: 13.5px;
          line-height: 1.5;
          color: var(--ink-soft);
        }
        .oc-attorney-question {
          font-size: 14.5px;
          color: var(--ink);
          font-style: italic;
          line-height: 1.55;
        }
        .oc-em { font-style: italic; color: var(--ink); }

        .oc-legal { border-top: 1px solid var(--line-soft); }
        .oc-legal-toggle {
          display: flex;
          align-items: center;
          gap: 7px;
          width: 100%;
          background: none;
          border: none;
          padding: 0.875rem 0 0.5rem;
          cursor: pointer;
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 12.5px;
          font-weight: 500;
          color: var(--ink-soft);
          transition: color 0.15s;
        }
        .oc-legal-toggle:hover { color: var(--ink); }
        .oc-legal-icon { width: 14px; height: 14px; stroke-width: 2; }
        .oc-chevron {
          width: 14px; height: 14px; stroke-width: 2;
          margin-left: auto;
          transition: transform 0.2s ease;
        }
        .oc-chevron-open { transform: rotate(180deg); }
        .oc-legal-body {
          font-size: 14px;
          color: var(--ink-soft);
          padding-bottom: 0.5rem;
          animation: oc-reveal 0.2s ease;
        }
        .oc-legal-body p { margin: 0 0 0.625rem; }
        .oc-outcome {
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 12px;
          display: flex;
          align-items: baseline;
          gap: 8px;
        }
        .oc-outcome-label {
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--amber);
          background: var(--amber-wash);
          padding: 2px 7px;
          border-radius: 2px;
        }

        .oc-disclaimer {
          margin: 0.875rem 0 0;
          padding-top: 0.875rem;
          border-top: 1px solid var(--line-soft);
          font-family: "Söhne", ui-sans-serif, system-ui, sans-serif;
          font-size: 11px;
          line-height: 1.5;
          color: #8A9389;
        }

        @keyframes oc-reveal {
          from { opacity: 0; transform: translateY(-3px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 520px) {
          .oc { padding: 1.25rem 1.25rem 1.125rem; }
          .oc-case { font-size: 1.25rem; }
          .oc-next { grid-template-columns: 1fr; }
        }
        @media (prefers-reduced-motion: reduce) {
          .oc-chevron, .oc-legal-body { transition: none; animation: none; }
        }
      `}</style>
    </article>
  );
}
