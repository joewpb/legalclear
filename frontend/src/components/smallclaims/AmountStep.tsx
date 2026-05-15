import { useWizard } from "./WizardContext";

export const SMALL_CLAIMS_LIMIT = 8000;
export const OVER_LIMIT_MESSAGE =
  "This exceeds Florida's small claims limit of $8,000. You'll need to file in County Civil Court instead.";

export default function AmountStep() {
  const { data, setField, next, back } = useWizard();
  const parsed = data.amount === "" ? NaN : Number(data.amount);
  const overLimit = !Number.isNaN(parsed) && parsed > SMALL_CLAIMS_LIMIT;
  const underLimit = !Number.isNaN(parsed) && parsed <= 0;
  const valid =
    !Number.isNaN(parsed) && parsed > 0 && parsed <= SMALL_CLAIMS_LIMIT;

  return (
    <section style={{ padding: 32 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
        How much are you claiming?
      </h2>
      <label
        style={{ display: "block", color: "var(--muted)", marginBottom: 8 }}
      >
        Amount claimed (USD)
      </label>
      <input
        type="number"
        className="input"
        inputMode="decimal"
        min={0}
        max={SMALL_CLAIMS_LIMIT}
        step="0.01"
        value={data.amount}
        onChange={(e) => setField("amount", e.target.value)}
        style={{ width: "100%", maxWidth: 280, fontFamily: "var(--font-mono)" }}
      />
      {overLimit && (
        <p
          style={{
            color: "var(--danger)",
            marginTop: 12,
            border: "1px solid var(--danger)",
            padding: 12,
            fontSize: 14,
          }}
          role="alert"
        >
          {OVER_LIMIT_MESSAGE}
        </p>
      )}
      {underLimit && (
        <p style={{ color: "var(--danger)", marginTop: 12, fontSize: 14 }}>
          Amount must be greater than $0.
        </p>
      )}
      <div
        style={{
          marginTop: 24,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <button className="btn" onClick={back}>
          ← BACK
        </button>
        <button
          className="btn"
          onClick={next}
          disabled={!valid}
          style={{ opacity: valid ? 1 : 0.4 }}
        >
          NEXT →
        </button>
      </div>
    </section>
  );
}
