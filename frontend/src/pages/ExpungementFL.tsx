import { useState } from "react";
import { Link } from "react-router-dom";
import EligibilityQuiz, {
  QuizAnswers,
} from "../components/expungement/EligibilityQuiz";
import ResultDisplay, {
  EligibilityResult,
} from "../components/expungement/ResultDisplay";

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8001";

export default function ExpungementFL() {
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAnswers, setLastAnswers] = useState<QuizAnswers | null>(null);

  async function submitQuiz(answers: QuizAnswers) {
    setSubmitting(true);
    setError(null);
    setLastAnswers(answers);
    try {
      const r = await fetch(`${API_URL}/api/expungement/eligibility`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(answers),
      });
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      setResult((await r.json()) as EligibilityResult);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <header className="hub-header">
        <h1>EXPUNGEMENT (FL)</h1>
        <p>Find out if you can seal or expunge a Florida record.</p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>
      <main className="hub-main">
        {!result && (
          <EligibilityQuiz onSubmit={submitQuiz} submitting={submitting} />
        )}
        {error && !result && (
          <p
            role="alert"
            style={{
              margin: 32,
              padding: 12,
              border: "1px solid var(--danger)",
              color: "var(--danger)",
            }}
          >
            {error}
          </p>
        )}
        {result && lastAnswers && (
          <ResultDisplay
            result={result}
            quizPayload={lastAnswers as unknown as Record<string, string>}
            onRestart={() => {
              setResult(null);
              setError(null);
              setLastAnswers(null);
            }}
          />
        )}
      </main>
      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Nothing here is legal
          advice. Using this site does not create an attorney-client
          relationship. For your specific situation, consult a licensed Florida
          attorney.
        </p>
      </footer>
    </>
  );
}
