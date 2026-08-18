import { useState } from "react";
import { Link } from "react-router-dom";
import SearchBar from "../components/caselaw/SearchBar";
import ResultsList from "../components/caselaw/ResultsList";
import type { CaseSearchResponse } from "../components/caselaw/types";
import { EXAMPLE_SEARCHES, LEGAL_AID_LINKS } from "../components/caselaw/types";
import { DISCLAIMER_TEXT } from "../components/DisclaimerNote";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

export default function CaseLawLookupFL() {
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
        body: JSON.stringify({ query: q, court_filter: "all" }),
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
      {/* ---- HEADER — benefit-led, 425K secondary ---- */}
      <header className="hub-header">
        <h1>Florida Court Decisions</h1>
        <p style={{ maxWidth: "var(--max-prose)", lineHeight: 1.6 }}>
          Describe your legal issue in plain English — we'll search Florida
          court decisions for cases that may be relevant to your situation.
          Our database covers over 425,000 opinions from Florida courts,
          each with a plain-language summary.
        </p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        {/* ---- "I WAS JUST SERVED" CALLOUT ---- */}
        <section style={{ padding: "0 32px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              padding: "14px 16px",
              border: "1px solid var(--border)",
              borderLeft: "3px solid var(--accent)",
              background: "#F5F7FC",
              marginBottom: 8,
            }}
          >
            <div style={{ display: "grid", gap: 6, flex: 1 }}>
              <p
                style={{
                  margin: 0,
                  fontSize: 14,
                  fontWeight: 600,
                  lineHeight: 1.4,
                }}
              >
                Just served with court papers?
              </p>
              <p
                style={{
                  margin: 0,
                  fontSize: 13,
                  color: "var(--muted)",
                  lineHeight: 1.5,
                }}
              >
                You may have a limited time to respond — sometimes as little
                as 5 days. Handle that first; case-law research can wait.
              </p>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 12,
                  marginTop: 4,
                }}
              >
                <Link
                  to="/upload"
                  style={{ fontSize: 13, color: "var(--accent)", fontWeight: 500 }}
                >
                  Find your response deadline →
                </Link>
                <Link
                  to="/landlord"
                  style={{ fontSize: 13, color: "var(--accent)", fontWeight: 500 }}
                >
                  Facing eviction? Eviction defense →
                </Link>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 12,
                  marginTop: 2,
                }}
              >
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
              </div>
            </div>
          </div>
        </section>

        {/* ---- SEARCH ---- */}
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
        </section>

        {/* ---- RESULTS AREA ---- */}
        <section style={{ padding: "0 32px 32px", display: "grid", gap: 16 }}>

          {/* ---- EMPTY STATE ---- */}
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

          {/* ---- STILL GOOD LAW? — guidance-first, not fear-first ---- */}
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
                <strong>The most recent cases carry the most weight.</strong>{" "}
                Older cases may still apply, but you should double-check them
                before relying on them. Courts can overturn, limit, or
                supersede earlier decisions — so read the newest cases on
                your topic first, and confirm a case is still good law
                before you use it. Each result below includes a free way to
                verify.
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

        {/* ---- HOW TO READ A CASE ---- */}
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
                  <li>{DISCLAIMER_TEXT}</li>
                </ul>
              </div>
            </div>
          </details>
        </section>
      </main>

      {/* ---- CONSOLIDATED DISCLAIMER — legal aid links moved up ---- */}
      <footer className="page-disclaimer">
        <p style={{ margin: 0, lineHeight: 1.6 }}>
          {DISCLAIMER_TEXT} Case law results are a starting point — not the
          final word. Always read the full opinion and verify it applies to
          your situation. Free legal-aid resources are linked at the top of
          this page.
        </p>
      </footer>
    </>
  );
}
