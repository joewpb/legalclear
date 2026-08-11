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

function lawIndicator(
  age: number | null,
  citeCount: number,
): { emoji: string; bg: string; border: string; text: React.ReactNode } {
  const isOld = age !== null && age > 15;
  const isHighCite = citeCount >= 50;

  // 2×2 matrix: age × citation count
  if (!isOld && isHighCite) {
    return {
      emoji: "🟢",
      bg: "#F0F7F4",
      border: "#166534",
      text: (
        <>
          Widely cited ({citeCount} times) — unlikely to have been overruled
          without notice. Still, any case can be reversed.{" "}
          <a
            href="https://scholar.google.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", fontWeight: 500 }}
          >
            Quick check on Google Scholar →
          </a>
        </>
      ),
    };
  }
  if (!isOld && !isHighCite) {
    return {
      emoji: "ℹ️",
      bg: "#F0F7F4",
      border: "#166534",
      text: (
        <>
          Cited {citeCount} {citeCount === 1 ? "time" : "times"} — not heavily
          referenced. Worth a quick check before relying on it.{" "}
          <a
            href="https://scholar.google.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", fontWeight: 500 }}
          >
            Google Scholar "How cited" →
          </a>
        </>
      ),
    };
  }
  if (isOld && isHighCite) {
    return {
      emoji: "🟡",
      bg: "#FFF7ED",
      border: "#F59E0B",
      text: (
        <>
          Over {age} years old but widely cited ({citeCount} times) — may
          still be good law. Later decisions may have limited or distinguished
          it.{" "}
          <a
            href="https://scholar.google.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", fontWeight: 500 }}
          >
            Verify on Google Scholar →
          </a>
        </>
      ),
    };
  }
  // Old + low cite
  return {
    emoji: "🔴",
    bg: "#FFF7ED",
    border: "#B91C1C",
    text: (
      <>
        Over {age} years old and cited only {citeCount}{" "}
        {citeCount === 1 ? "time" : "times"} — higher risk of being
        overruled or superseded.{" "}
        <strong>Verify before relying on it.</strong>{" "}
        <a
          href="https://scholar.google.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "var(--accent)", fontWeight: 500 }}
        >
          Check on Google Scholar →
        </a>{" "}
        Your local county law library can also help, free of charge.
      </>
    ),
  };
}

export default function ResultCard({ r }: { r: CaseResult }) {
  const age = ageInYears(r.date_filed);
  const indicator = lawIndicator(age, r.cite_count ?? 0);

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
          <div style={{ marginTop: 2 }}>
            Cited {r.cite_count ?? 0}{" "}
            {(r.cite_count ?? 0) === 1 ? "time" : "times"}
          </div>
        </div>
      </header>

      {r.plain_english_summary ? (
        <p style={{ margin: 0, lineHeight: 1.5, fontSize: 14 }}>
          {r.plain_english_summary}
        </p>
      ) : (
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
          We don't have a plain-language summary for this one yet — open the
          full opinion to read it.
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
