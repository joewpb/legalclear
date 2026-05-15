import { useState } from "react";
import { Link } from "react-router-dom";
import UploadInterface from "../components/policereport/UploadInterface";
import FindingsList from "../components/policereport/FindingsList";
import type { Finding } from "../components/policereport/FindingCard";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

type AnalyzeResponse = {
  findings: Finding[];
  documents_analyzed: number;
};

export default function PoliceReportAnalyzer() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function analyze(primary: File, supplementary: File[]) {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("files", primary, primary.name);
      for (const s of supplementary) fd.append("files", s, s.name);
      const r = await fetch(`${API_URL}/api/police-report/analyze`, {
        method: "POST",
        body: fd,
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setResult((await r.json()) as AnalyzeResponse);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="hub-header">
        <h1>POLICE REPORT ANALYZER</h1>
        <p>
          Upload a police report (and any related documents). The scanner
          flags procedural and factual discrepancies a defense attorney would
          want to investigate. This is NOT legal advice.
        </p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        {!result && (
          <UploadInterface
            onAnalyze={analyze}
            submitting={submitting}
            error={error}
          />
        )}

        {result && (
          <>
            <FindingsList
              findings={result.findings}
              documentsAnalyzed={result.documents_analyzed}
            />
            <div style={{ padding: "0 32px 32px" }}>
              <button
                className="btn"
                onClick={() => setResult(null)}
                style={{ padding: "8px 16px" }}
              >
                ← ANALYZE ANOTHER REPORT
              </button>
            </div>
          </>
        )}
      </main>

      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. The Scanner Agent
          highlights document discrepancies — it does not assess your defense
          or recommend a strategy. Always review findings with a licensed
          Florida criminal-defense attorney.
        </p>
      </footer>
    </>
  );
}
