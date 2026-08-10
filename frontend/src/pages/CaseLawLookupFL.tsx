import { useState } from "react";
import { Link } from "react-router-dom";
import SearchBar from "../components/caselaw/SearchBar";
import CourtFilter from "../components/caselaw/CourtFilter";
import ResultsList from "../components/caselaw/ResultsList";
import type {
  CaseSearchResponse,
  CourtFilterValue,
} from "../components/caselaw/types";
import { EXAMPLE_SEARCHES, LEGAL_AID_LINKS } from "../components/caselaw/types";

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

  const hasSearched = response !== null || error !== null;

  return (
    <>
      {/* ---- HEADER (change 1: plain language) ---- */}
      <header className="hub-header">
        <h1>Florida Court Decisions</h1>
        <p style={{ maxWidth: "var(--max-prose)", lineHeight: 1.6 }}>
          Search over 425,000 Florida court opinions. Describe your legal
          issue in plain English — we'll find cases that may be relevant,
          each with a plain-language summary.
        </p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        {/* ---- SEARCH + FILTER ---- */}
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

        {/* ---- RESULTS AREA ---- */}
        <section style={{ padding: "0 32px 32px", display: "grid", gap: 16 }}>

          {/* ---- EMPTY STATE (change 3: clickable examples) ---- */}
          {!hasSearched && (
            <div
              style={{
                border: "1px solid var(--border)",
                padding: "24px 20px",
                display: "grid",
                gap: 14,
              }}
            >
              <h2
                style={{
                  fontFamily: "var(--font-sans)",
                  fontWeight: 600,
                  fontSize: 16,
                  margin: 0,
                  color: "var(--fg)",
                }}
              >
                Not sure what to search for? Try one of these:
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
                  gap: 8,
                }}
              >
                {EXAMPLE_SEARCHES.map((ex) => (
                  <button
                    key={ex.query}
                    type="button"
                    onClick={() => runSearch(ex.query)}
                    disabled={submitting}
                    style={{
                      textAlign: "left",
                      padding: "10px 14px",
                      border: "1px solid var(--border-strong)",
                      borderRadius: 4,
                      background: "#FFFFFF",
                      cursor: "pointer",
                      fontFamily: "var(--font-sans)",
                      fontSize: 13,
                      lineHeight: 1.4,
                      color: "var(--fg)",
                      transition: "border-color 150ms ease, background 150ms ease",
                    }}
                    onMouseEnter={(e) => {
                      (e.target as HTMLElement).style.borderColor =
                        "var(--accent)";
                      (e.target as HTMLElement).style.background = "#F5F7FC";
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLElement).style.borderColor =
                        "var(--border-strong)";
                      (e.target as HTMLElement).style.background = "#FFFFFF";
                    }}
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ---- ERROR ---- */}
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

          {/* ---- STILL GOOD LAW? WARNING (change 2) ---- */}
          {response && response.results.length > 0 && (
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                padding: "12px 14px",
                border: "1px solid #FCD34D",
                background: "#FFFBEB",
                fontSize: 13,
                lineHeight: 1.5,
              }}
            >
              <span style={{ fontSize: 16 }}>⚠️</span>
              <span>
                <strong>Cases can be overturned.</strong> A later court
                decision may have overruled, limited, or superseded any of
                the cases below. Before relying on a case, verify it is
                still good law. Florida Bar members can check this using
                Shepard's or KeyCite. If you don't have access to those
                tools, read the most recent cases first — they're less
                likely to have been overturned.
              </span>
            </div>
          )}

          {/* ---- RESULTS ---- */}
          {response && (
            <ResultsList
              query={response.query}
              results={response.results}
              totalResults={response.total_results}
            />
          )}
        </section>

        {/* ---- HOW TO READ A CASE (change 7: collapsible primer) ---- */}
        <section style={{ padding: "0 32px 32px" }}>
          <details
            style={{
              border: "1px solid var(--border)",
              padding: 0,
            }}
          >
            <summary
              style={{
                padding: "14px 16px",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                fontWeight: 600,
                fontSize: 15,
                color: "var(--fg)",
                userSelect: "none",
              }}
            >
              How to read a court case
            </summary>
            <div
              style={{
                padding: "4px 16px 18px",
                fontSize: 14,
                lineHeight: 1.7,
                color: "var(--fg)",
                display: "grid",
                gap: 14,
              }}
            >
              <div>
                <h4
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontWeight: 600,
                    fontSize: 14,
                    margin: "0 0 4px",
                  }}
                >
                  Case names (like Smith v. Jones)
                </h4>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  The name before the "v." is the person who sued (the
                  plaintiff). The name after is the person being sued (the
                  defendant). In criminal cases, it's usually "State v.
                  Defendant" or "Florida v. Defendant."
                </p>
              </div>

              <div>
                <h4
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontWeight: 600,
                    fontSize: 14,
                    margin: "0 0 4px",
                  }}
                >
                  Citations (like 123 So. 3d 456)
                </h4>
                <p style={{ margin: 0, color: "var(--muted)" }}>
                  This is like a library call number for the case. "So."
                  stands for Southern Reporter — the book series where
                  Florida cases are published. The first number is the
                  volume, the second is the series, and the third is the
                  page number. You don't need to understand citations to
                  read the case — just know it's how lawyers and courts
                  reference the decision.
                </p>
              </div>

              <div>
                <h4
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontWeight: 600,
                    fontSize: 14,
                    margin: "0 0 4px",
                  }}
                >
                  How to use what you find
                </h4>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    color: "var(--muted)",
                    display: "grid",
                    gap: 6,
                  }}
                >
                  <li>
                    Read the plain-English summary first — it tells you what
                    the case decided.
                  </li>
                  <li>
                    If the case seems relevant, read the full opinion
                    (linked on each result card).
                  </li>
                  <li>
                    When citing a case in court, you need the full citation
                    and a quote from the opinion supporting your point.
                  </li>
                  <li>
                    The most recent cases on a topic carry the most weight.
                    Older cases may still be good law, but you should verify
                    they haven't been overturned.
                  </li>
                  <li>
                    This is legal information, not legal advice. If you plan
                    to argue a case in court, consulting a Florida attorney
                    will give you the strongest foundation.
                  </li>
                </ul>
              </div>
            </div>
          </details>
        </section>
      </main>

      {/* ---- CONSOLIDATED DISCLAIMER (change 5) ---- */}
      <footer className="page-disclaimer">
        <p style={{ margin: 0, lineHeight: 1.6 }}>
          LegalClear is an informational tool, not legal advice. Using this
          site does not create an attorney-client relationship. Case law
          results are a starting point for research — always read the full
          opinion before relying on a case. Need a lawyer?
        </p>
        <p style={{ margin: "8px 0 0", display: "flex", flexWrap: "wrap", gap: 16 }}>
          {LEGAL_AID_LINKS.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, color: "var(--accent)" }}
            >
              {link.label} →
            </a>
          ))}
        </p>
      </footer>
    </>
  );
}
