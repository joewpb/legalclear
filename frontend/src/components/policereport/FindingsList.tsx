import FindingCard from "./FindingCard";
import type { Finding } from "./FindingCard";

type Props = {
  findings: Finding[];
  documentsAnalyzed: number;
};

export default function FindingsList({ findings, documentsAnalyzed }: Props) {
  return (
    <section style={{ padding: "0 32px 32px", display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 4 }}>
        <h2 className="mono" style={{ fontSize: 18, margin: 0 }}>
          ANALYSIS RESULTS
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          {documentsAnalyzed} document{documentsAnalyzed === 1 ? "" : "s"}{" "}
          analyzed · {findings.length} finding
          {findings.length === 1 ? "" : "s"}
        </p>
      </header>

      {findings.length === 0 ? (
        <p
          style={{
            border: "1px solid var(--border)",
            padding: 16,
            color: "var(--muted)",
          }}
        >
          No findings flagged. This does not mean the documents are flawless —
          it means the scanner did not detect issues it could surface. Always
          review with a licensed Florida attorney.
        </p>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {findings.map((f, i) => (
            <FindingCard key={i} f={f} />
          ))}
        </div>
      )}
    </section>
  );
}
