import { Link } from "react-router-dom";

export type PhaseStubProps = {
  title: string;
  phase: string; // e.g. "Phase 16"
};

// Placeholder route page for Part B tiles not yet built. Replaced by the
// real page in its owning phase. Phase 15 only requires the route to
// resolve and render *something*.
export default function PhaseStub({ title, phase }: PhaseStubProps) {
  return (
    <>
      <header className="hub-header">
        <h1>{title}</h1>
        <p>Coming in {phase}.</p>
      </header>
      <main className="hub-main" style={{ padding: "32px" }}>
        <Link to="/" className="btn">
          ← Back to hub
        </Link>
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
