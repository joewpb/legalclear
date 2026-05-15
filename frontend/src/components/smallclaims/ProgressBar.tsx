import { useWizard } from "./WizardContext";

const TOTAL = 5;

export default function ProgressBar() {
  const { step } = useWizard();
  return (
    <div style={{ padding: "16px 32px", borderBottom: "1px solid var(--border)" }}>
      <p
        className="mono"
        style={{ margin: "0 0 8px", fontSize: 12, letterSpacing: "0.08em" }}
      >
        STEP {step} OF {TOTAL}
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${TOTAL}, 1fr)`,
          gap: 4,
        }}
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={TOTAL}
        aria-valuenow={step}
      >
        {Array.from({ length: TOTAL }, (_, i) => (
          <span
            key={i}
            style={{
              height: 4,
              background: i < step ? "var(--accent)" : "var(--border-strong)",
            }}
          />
        ))}
      </div>
    </div>
  );
}
