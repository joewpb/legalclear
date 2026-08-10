import ResultCard from "./ResultCard";
import type { CaseResult } from "./types";

type Props = {
  query: string;
  results: CaseResult[];
  totalResults: number;
};

function countLabel(shown: number, total: number): string | null {
  if (shown === 0) return null; // suppress — the friendly empty block handles it
  if (total === 1) return "1 result";
  if (shown === total) return `Showing all ${total} results`;
  return `Showing the ${shown} closest matches out of ${total}`;
}

export default function ResultsList({ query, results, totalResults }: Props) {
  const label = countLabel(results.length, totalResults);

  return (
    <section style={{ display: "grid", gap: 12 }}>
      <header style={{ display: "grid", gap: 4 }}>
        <h2
          style={{
            fontFamily: "var(--font-serif)",
            fontWeight: 500,
            fontSize: 20,
            margin: 0,
          }}
        >
          Results for “{query}”
        </h2>
        {label && (
          <p style={{ color: "var(--muted)", fontSize: 12, margin: 0 }}>
            {label}
          </p>
        )}
      </header>

      {results.length === 0 ? (
        <div
          style={{
            border: "1px solid var(--border)",
            padding: "20px 16px",
            display: "grid",
            gap: 8,
          }}
        >
          <p style={{ margin: 0, lineHeight: 1.5 }}>
            No Florida court decisions matched your search. Try:
          </p>
          <ul
            style={{
              margin: 0,
              paddingLeft: 20,
              fontSize: 14,
              color: "var(--muted)",
              display: "grid",
              gap: 4,
            }}
          >
            <li>Different or broader keywords</li>
            <li>
              Removing the court filter (set it to "All Florida courts")
            </li>
            <li>Checking your spelling — legal terms can be tricky</li>
          </ul>
        </div>
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
