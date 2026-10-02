import { useState } from "react";
import type { CaseResult, CitationTreatment } from "./types";

function ageInYears(dateStr: string): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  const now = new Date();
  let years = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) years--;
  // Corrupt dates (e.g. year 0014) compute absurd ages — treat as unknown.
  if (years < 0 || years > 120) return null;
  return years;
}

const TREATMENT_LABELS: Record<CitationTreatment["type"], string> = {
  overruled: "Overruled",
  reversed: "Reversed",
  superseded: "Superseded",
  abrogated: "Abrogated",
  criticized: "Criticized",
  questioned: "Questioned",
  other: "Negative treatment",
};

function treatmentIndicator(
  treatments: CitationTreatment[],
): { emoji: string; bg: string; border: string; text: string } {
  const primary = treatments[0];
  const label = TREATMENT_LABELS[primary.type] || "Negative treatment";
  const count = treatments.length;
  const suffix = count > 1
    ? ` (+${count - 1} other negative treatment${count > 2 ? "s" : ""})`
    : "";
  return {
    emoji: "🔴",
    bg: "#FEF2F2",
    border: "#B91C1C",
    text:
      `Later court treatment: ${label}${suffix} — ${primary.text}`,
  };
}

function lawIndicator(
  age: number | null,
  citeCount: number,
): { emoji: string; bg: string; border: string; text: React.ReactNode } {
  if (age === null) {
    return {
      emoji: "ℹ️",
      bg: "#F5F7FC",
      border: "#4B5563",
      text:
        `Decision date not available — this case has been cited ${citeCount} ` +
        `${citeCount === 1 ? "time" : "times"}. Verify before relying on it.`,
    };
  }
  const isOld = age > 15;
  const isHighCite = citeCount >= 50;

  // 2×2 matrix: age × citation count
  if (!isOld && isHighCite) {
    return {
      emoji: "🟢",
      bg: "#F0F7F4",
      border: "#166534",
      text:
        `Widely cited (${citeCount} times) — unlikely to have ` +
        "been overruled without notice. Still, any case can be reversed.",
    };
  }
  if (!isOld && !isHighCite) {
    return {
      emoji: "ℹ️",
      bg: "#F0F7F4",
      border: "#166534",
      text:
        `Cited ${citeCount} ${citeCount === 1 ? "time" : "times"} — ` +
        "not heavily referenced. Worth verifying before relying on it.",
    };
  }
  if (isOld && isHighCite) {
    return {
      emoji: "🟡",
      bg: "#FFF7ED",
      border: "#F59E0B",
      text:
        `Over ${age} years old but widely cited (${citeCount} times) — ` +
        "may still be good law. Later decisions may have limited or " +
        "distinguished it.",
    };
  }
  // Old + low cite
  return {
    emoji: "🔴",
    bg: "#FFF7ED",
    border: "#B91C1C",
    text:
      `Over ${age} years old and cited only ${citeCount} ` +
      `${citeCount === 1 ? "time" : "times"} — higher risk of being ` +
      "overruled or superseded. Verify before relying on it.",
  };
}

// Long raw summaries (the corpus stores decision text) render as an excerpt
// with an on-site expander — no external links on result cards.
const EXCERPT_CHARS = 400;

function summaryExcerpt(text: string): { head: string; rest: string | null } {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= EXCERPT_CHARS) return { head: clean, rest: null };
  return { head: clean.slice(0, EXCERPT_CHARS), rest: clean.slice(EXCERPT_CHARS) };
}

export default function ResultCard({ r }: { r: CaseResult }) {
  const [expanded, setExpanded] = useState(false);
  const age = ageInYears(r.date_filed || "");
  const treatments = r.citation_treatment;
  const indicator = treatments && treatments.length > 0
    ? treatmentIndicator(treatments)
    : lawIndicator(age, r.cite_count ?? 0);

  const summary = r.plain_english_summary;
  const excerpt = summary ? summaryExcerpt(summary) : null;

  return (
    <article
      style={{
        border: "1px solid var(--border)",
        padding: 16,
        display: "grid",
        gap: 8,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
        }}
      >
        <div style={{ display: "grid", gap: 4, minWidth: 0, flex: 1 }}>
          <h3
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 500,
              fontSize: 18,
              margin: 0,
              wordBreak: "break-word",
              lineHeight: 1.2,
            }}
          >
            {r.case_name}
          </h3>
          <p
            style={{
              color: "var(--muted)",
              fontSize: 12,
              margin: 0,
            }}
          >
            {r.citation}
          </p>
        </div>
        <div
          style={{
            textAlign: "right",
            color: "var(--muted)",
            fontSize: 12,
            flexShrink: 0,
            maxWidth: "40%",
          }}
        >
          <div>{r.court}</div>
          <div>{r.date_filed || "Date not available"}</div>
          <div style={{ marginTop: 2 }}>
            Cited {r.cite_count ?? 0}{" "}
            {(r.cite_count ?? 0) === 1 ? "time" : "times"}
          </div>
        </div>
      </header>

      {excerpt ? (
        <>
          <p style={{ margin: 0, lineHeight: 1.5, fontSize: 14 }}>
            {expanded ? summary : `${excerpt.head}…`}
          </p>
          {excerpt.rest && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="btn-outline"
              style={{
                justifySelf: "start",
                textDecoration: "none",
                padding: "6px 12px",
                fontSize: 12,
                marginTop: 0,
                border: "1px solid var(--border-strong)",
                borderRadius: 4,
                color: "var(--fg)",
                fontFamily: "var(--font-sans)",
                fontWeight: 500,
                cursor: "pointer",
                background: "transparent",
              }}
            >
              {expanded ? "Show less" : "Read more of this decision"}
            </button>
          )}
        </>
      ) : (
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
          No summary text is available for this decision yet.
        </p>
      )}

      {/* Good-law indicator — 2×2 matrix: age × cite_count */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
          padding: "8px 10px",
          background: indicator.bg,
          borderLeft: `3px solid ${indicator.border}`,
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        <span style={{ fontSize: 14 }}>{indicator.emoji}</span>
        <span style={{ color: "var(--fg)" }}>{indicator.text}</span>
      </div>
    </article>
  );
}
