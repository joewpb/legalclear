import { useWizard } from "./WizardContext";

const DEFENDANT_TYPES = ["Individual", "Business", "Both"];

export default function DefendantStep() {
  const { data, setField, next, back } = useWizard();
  const valid =
    data.defendant_name.trim().length > 0 &&
    data.defendant_address.trim().length > 0;

  return (
    <section style={{ padding: 32 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
        Who are you suing?
      </h2>

      <fieldset style={{ border: 0, padding: 0, marginBottom: 16 }}>
        <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
          Defendant type
        </legend>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {DEFENDANT_TYPES.map((t) => (
            <label
              key={t}
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                border: "1px solid var(--border)",
                padding: "8px 16px",
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="defendant_type"
                value={t}
                checked={data.defendant_type === t}
                onChange={(e) => setField("defendant_type", e.target.value)}
              />
              <span>{t}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div style={{ display: "grid", gap: 16 }}>
        <label>
          <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
            Defendant name <span style={{ color: "var(--danger)" }}>*</span>
          </span>
          <input
            className="input"
            value={data.defendant_name}
            onChange={(e) => setField("defendant_name", e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
            Defendant address <span style={{ color: "var(--danger)" }}>*</span>
          </span>
          <textarea
            className="input"
            value={data.defendant_address}
            onChange={(e) => setField("defendant_address", e.target.value)}
            style={{ width: "100%", minHeight: 72, fontFamily: "var(--font-sans)" }}
          />
        </label>
        <label>
          <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
            Phone (optional)
          </span>
          <input
            className="input"
            type="tel"
            value={data.defendant_phone}
            onChange={(e) => setField("defendant_phone", e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
            Email (optional)
          </span>
          <input
            className="input"
            type="email"
            value={data.defendant_email}
            onChange={(e) => setField("defendant_email", e.target.value)}
            style={{ width: "100%" }}
          />
        </label>
      </div>

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
