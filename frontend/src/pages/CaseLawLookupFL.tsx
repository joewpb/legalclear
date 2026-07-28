import { useState } from "react";
import { Link } from "react-router-dom";
import SearchBar from "../components/caselaw/SearchBar";
import CourtFilter from "../components/caselaw/CourtFilter";
import ResultsList from "../components/caselaw/ResultsList";
import type {
  CaseSearchResponse,
  CourtFilterValue,
} from "../components/caselaw/types";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

export default function CaseLawLookupFL() {
  const [court, setCourt] = useState<CourtFilterValue>("all");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<CaseSearchResponse | null>(null);

  async function runSearch(q: string) {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API_URL}/api/case-law/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, court_filter: court }),
      });
      if (r.status === 502) {
        throw new Error(
          "The case-law service is temporarily unavailable. Try again in a moment.",
        );
      }
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setResponse((await r.json()) as CaseSearchResponse);
    } catch (e) {
      setError((e as Error).message);
      setResponse(null);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="hub-header">
        <h1>FL CASE LAW LOOKUP</h1>
        <p>
          Search 759 curated Florida opinions in LegalClear's case-law
          corpus. Case names, citations, and summaries come straight from
          the corpus — nothing is invented. (CourtListener is used only as
          an optional fallback when configured.)
        </p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        <section
          style={{
            padding: 32,
            display: "grid",
            gap: 16,
            gridTemplateColumns: "1fr",
          }}
        >
          <SearchBar
            initial=""
            onSearch={runSearch}
            submitting={submitting}
          />
          <CourtFilter value={court} onChange={setCourt} />
        </section>

        <section style={{ padding: "0 32px 32px", display: "grid", gap: 16 }}>
          <p
            style={{
              border: "1px solid var(--border)",
              padding: 12,
              color: "var(--muted)",
              fontSize: 13,
              margin: 0,
            }}
          >
            Results from LegalClear's Florida case-law corpus. Always verify
            by reading the full opinion.
          </p>

          {error && (
            <p
              role="alert"
              style={{
                color: "var(--danger)",
                border: "1px solid var(--danger)",
                padding: 12,
                margin: 0,
              }}
            >
              {error}
            </p>
          )}

          {response && (
            <ResultsList
              query={response.query}
              results={response.results}
              totalResults={response.total_results}
            />
          )}
        </section>
      </main>

      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Case law results are
          a starting point for legal research, not a substitute for it.
          Always read the full opinion and consult a licensed Florida
          attorney before relying on any case.
        </p>
      </footer>
    </>
  );
}
