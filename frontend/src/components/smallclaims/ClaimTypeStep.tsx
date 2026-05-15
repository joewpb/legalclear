import { useWizard } from "./WizardContext";

const CLAIM_TYPES = [
  "Unpaid debt",
  "Property damage",
  "Security deposit",
  "Breach of contract",
  "Minor personal injury",
  "Other",
];

export default function ClaimTypeStep() {
  const { data, setField, next } = useWizard();
  const canAdvance = data.claim_type.length > 0;

  return (
    <section style={{ padding: 32 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
        What kind of claim is this?
      </h2>
      <fieldset
        style={{ border: 0, padding: 0, display: "grid", gap: 12 }}
      >
        <legend style={{ position: "absolute", left: "-9999px" }}>
          Claim type
        </legend>
        {CLAIM_TYPES.map((t) => (
          <label
            key={t}
            style={{
              display: "flex",
              gap: 12,
              alignItems: "center",
              border: "1px solid var(--border)",
              padding: 12,
              cursor: "pointer",
            }}
          >
            <input
              type="radio"
              name="claim_type"
              value={t}
              checked={data.claim_type === t}
              onChange={(e) => setField("claim_type", e.target.value)}
            />
            <span>{t}</span>
          </label>
        ))}
      </fieldset>
      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button
          className="btn"
          onClick={next}
          disabled={!canAdvance}
          style={{ opacity: canAdvance ? 1 : 0.4 }}
        >
          NEXT →
        </button>
      </div>
    </section>
  );
}
