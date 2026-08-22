import { useState } from "react";
import { Link } from "react-router-dom";
import CitationTypeStep from "../components/traffic/CitationTypeStep";
import OptionsStep from "../components/traffic/OptionsStep";
import GenerateStep from "../components/traffic/GenerateStep";
import type { TrafficForm } from "../components/traffic/types";
import { DISCLAIMER_TEXT } from "../components/DisclaimerNote";

const INITIAL: TrafficForm = {
  citation_type: "",
  citation_number: "",
  issue_date: "",
  county: "",
  first_offense_12mo: false,
  chosen_path: "",
};

export default function TrafficFL() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [form, setForm] = useState<TrafficForm>(INITIAL);

  return (
    <>
      <header className="hub-header">
        <h1>TRAFFIC / TICKETS (FL)</h1>
        <p>Three resolution paths: pay, traffic school, or contest.</p>
        <p style={{ marginTop: 8 }}>
          <Link to="/" style={{ color: "var(--muted)", fontSize: 12 }}>
            ← Back to hub
          </Link>
        </p>
      </header>

      <main className="hub-main">
        <ProgressBar step={step} />
        {step === 1 && (
          <CitationTypeStep
            form={form}
            setForm={setForm}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <OptionsStep
            form={form}
            setForm={setForm}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <GenerateStep form={form} onBack={() => setStep(2)} />
        )}
      </main>

      <footer className="page-disclaimer">
        <p>
          {DISCLAIMER_TEXT}
        </p>
      </footer>
    </>
  );
}

function ProgressBar({ step }: { step: number }) {
  return (
    <div style={{ padding: "0 32px 16px" }}>
      <p
        className="mono"
        style={{ margin: "0 0 8px", fontSize: 12, letterSpacing: "0.08em" }}
      >
        STEP {step} OF 3
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 4,
        }}
      >
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            style={{
              height: 4,
              background: i <= step ? "var(--accent)" : "var(--border-strong)",
            }}
          />
        ))}
      </div>
    </div>
  );
}
