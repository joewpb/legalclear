import type { CaseResult } from "./types";

function ageInYears(dateStr: string): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  const now = new Date();
  let years = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) years--;
  return years;
}

export default function ResultCard({ r }: { r: CaseResult }) {
  const age = ageInYears(r.date_filed);
  const isOld = age !== null && age > 15;

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
          {r.citation && (
            <p
              style={{
                color: "var(--muted)",
                fontSize: 12,
                margin: 0,
              }}
              title="Volume · Reporter · Page — the official reference number for this case"
            >
              {r.citation}
            </p>
          )}
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
          {r.date_filed && <div>{r.date_filed}</div>}
        </div>
      </header>

      {r.plain_english_summary ? (
        <p style={{ margin: 0, lineHeight: 1.5, fontSize: 14 }}>
          {r.plain_english_summary}
        </p>
      ) : (
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
          No plain-English summary available
          {r.courtlistener_url
            ? ". Read the full opinion for details."
            : "."}
        </p>
      )}

      {/* Still good law? indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
          padding: "8px 10px",
          background: isOld ? "#FFF7ED" : "#F0F7F4",
          borderLeft: `3px solid ${isOld ? "#F59E0B" : "#166534"}`,
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        <span style={{ fontSize: 14 }}>{isOld ? "⚠️" : "ℹ️"}</span>
        <span style={{ color: "var(--fg)" }}>
          {isOld ? (
            <>
              This case is over {age} years old. It may have been overruled,
              limited, or superseded by later decisions.{" "}
              <strong>
                Before relying on it, verify it is still good law.
              </strong>
            </>
          ) : (
            <>
              Cases can be overturned at any time. Florida Bar members can use
              Shepard's or KeyCite to verify a case is still good law before
              relying on it.
            </>
          )}
        </span>
      </div>

      {r.courtlistener_url && (
        <a
          href={r.courtlistener_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-outline"
          style={{
            justifySelf: "start",
            textDecoration: "none",
            padding: "8px 16px",
            fontSize: 12,
            marginTop: 4,
            border: "1px solid var(--border-strong)",
            borderRadius: 4,
            color: "var(--fg)",
            fontFamily: "var(--font-sans)",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Read full opinion →
        </a>
      )}
    </article>
  );
}
