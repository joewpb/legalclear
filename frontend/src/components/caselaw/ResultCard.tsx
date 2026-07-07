import type { CaseResult } from "./types";

export default function ResultCard({ r }: { r: CaseResult }) {
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
            className="mono"
            style={{ fontSize: 18, margin: 0, wordBreak: "break-word" }}
          >
            {r.case_name}
          </h3>
          {r.citation ? (
            <p
              className="mono"
              style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}
            >
              {r.citation}
            </p>
          ) : (
            <p
              className="mono"
              style={{
                color: "var(--muted)",
                fontSize: 13,
                margin: 0,
                fontStyle: "italic",
              }}
            >
              Citation not available
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
        <p style={{ margin: 0, lineHeight: 1.5 }}>{r.plain_english_summary}</p>
      ) : (
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
          No plain-English summary available. Read the full opinion on
          CourtListener for context.
        </p>
      )}

      {r.courtlistener_url && (
        <a
          href={r.courtlistener_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn"
          style={{
            justifySelf: "start",
            textDecoration: "none",
            padding: "8px 16px",
            fontSize: 12,
            marginTop: 4,
          }}
        >
          VIEW ON COURTLISTENER →
        </a>
      )}
    </article>
  );
}
