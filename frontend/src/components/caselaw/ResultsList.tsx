import ResultCard from "./ResultCard";
import type { CaseResult } from "./types";

type Props = {
  query: string;
  results: CaseResult[];
  totalResults: number;
};

export default function ResultsList({ query, results, totalResults }: Props) {
  return (
    <section style={{ display: "grid", gap: 12 }}>
      <header style={{ display: "grid", gap: 4 }}>
        <h2 className="mono" style={{ fontSize: 16, margin: 0 }}>
          RESULTS FOR &ldquo;{query}&rdquo;
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: 0 }}>
          {results.length} shown · {totalResults} total in the Florida
          case-law corpus
        </p>
      </header>

      {results.length === 0 ? (
        <p
          style={{
            border: "1px solid var(--border)",
            padding: 16,
            color: "var(--muted)",
          }}
        >
          No matches in the Florida case-law corpus for that query. Try
          different keywords or broaden your court filter.
        </p>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {results.map((r, i) => (
            <ResultCard key={`${i}-${r.case_name}`} r={r} />
          ))}
        </div>
      )}
    </section>
  );
}
