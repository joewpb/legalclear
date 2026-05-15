// Severity badge — shared component, Phase 21.
// Colors per source spec:
//   HIGH   → --danger background, white text
//   MEDIUM → --accent background, black text
//   LOW    → --muted  background, white text

export type Severity = "high" | "medium" | "low" | string;

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const norm = (severity || "").toLowerCase();
  const palette =
    norm === "high"
      ? { bg: "var(--danger)", fg: "#fff" }
      : norm === "medium"
        ? { bg: "var(--accent)", fg: "#000" }
        : norm === "low"
          ? { bg: "var(--muted)", fg: "#fff" }
          : { bg: "var(--border-strong)", fg: "var(--fg)" };

  return (
    <span
      className="mono"
      style={{
        background: palette.bg,
        color: palette.fg,
        padding: "4px 8px",
        fontSize: 11,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        display: "inline-block",
      }}
    >
      {norm || "UNKNOWN"}
    </span>
  );
}
