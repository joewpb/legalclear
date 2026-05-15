import SeverityBadge from "../SeverityBadge";

export type Finding = {
  category: string;
  severity: string;
  page_reference: string;
  finding: string;
  ask_your_attorney_about: string;
};

export default function FindingCard({ f }: { f: Finding }) {
  return (
    <article
      style={{
        border: "1px solid var(--border)",
        padding: 16,
        display: "grid",
        gap: 12,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <SeverityBadge severity={f.severity} />
          <span
            className="mono"
            style={{
              fontSize: 12,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {f.category}
          </span>
        </div>
        <span style={{ color: "var(--muted)", fontSize: 12 }}>
          {f.page_reference}
        </span>
      </header>

      <p style={{ margin: 0, lineHeight: 1.5 }}>{f.finding}</p>

      <div
        style={{
          border: "1px solid var(--border)",
          padding: 12,
          background: "var(--bg-elevated, transparent)",
        }}
      >
        <p
          className="mono"
          style={{
            margin: "0 0 4px",
            fontSize: 11,
            color: "var(--muted)",
            letterSpacing: "0.08em",
          }}
        >
          ASK YOUR ATTORNEY ABOUT
        </p>
        <p style={{ margin: 0, lineHeight: 1.5 }}>
          {f.ask_your_attorney_about}
        </p>
      </div>
    </article>
  );
}
