import violations from "../../data/fl_traffic_violations.json";
import type { TrafficForm, Violation } from "./types";

const VIOLATIONS = violations as Violation[];

type Props = {
  form: TrafficForm;
  setForm: (f: TrafficForm) => void;
  onNext: () => void;
};

export default function CitationTypeStep({ form, setForm, onNext }: Props) {
  const v = VIOLATIONS.find((x) => x.type === form.citation_type);
  const isDui = form.citation_type === "DUI";
  const valid =
    form.citation_type.length > 0 &&
    form.citation_number.trim().length > 0 &&
    form.issue_date.length > 0;

  return (
    <section style={{ padding: 32, display: "grid", gap: 16 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
        Step 1 — Citation type + basics
      </h2>

      <fieldset style={{ border: 0, padding: 0 }}>
        <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
          What type of citation did you receive? *
        </legend>
        <div style={{ display: "grid", gap: 8 }}>
          {VIOLATIONS.map((x) => (
            <label
              key={x.type}
              style={{
                border: "1px solid var(--border)",
                padding: 12,
                display: "flex",
                gap: 12,
                alignItems: "center",
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="citation_type"
                checked={form.citation_type === x.type}
                onChange={() => setForm({ ...form, citation_type: x.type })}
              />
              <span style={{ flex: 1 }}>{x.type}</span>
              <span
                className="mono"
                style={{ color: "var(--muted)", fontSize: 12 }}
              >
                {x.is_criminal ? "CRIMINAL" : "CIVIL"} · {x.points} pts
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {isDui && (
        <p
          role="alert"
          style={{
            border: "2px solid var(--danger)",
            color: "var(--danger)",
            padding: 12,
            margin: 0,
          }}
        >
          DUI is a serious criminal charge. Strongly recommend consulting an
          attorney before choosing a path.
        </p>
      )}

      {v && !isDui && (
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Traffic school eligible:{" "}
          <span className="mono">
            {v.traffic_school_eligible ? "YES" : "NO"}
          </span>
        </p>
      )}

      <label>
        <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
          Citation number *
        </span>
        <input
          className="input"
          value={form.citation_number}
          onChange={(e) =>
            setForm({ ...form, citation_number: e.target.value })
          }
          style={{ width: "100%" }}
        />
      </label>

      <label>
        <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
          Issue date *
        </span>
        <input
          className="input"
          type="date"
          value={form.issue_date}
          onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
          style={{ width: "100%" }}
        />
      </label>

      {v?.traffic_school_eligible && (
        <label
          style={{
            border: "1px solid var(--border)",
            padding: 12,
            display: "flex",
            gap: 8,
            alignItems: "center",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={form.first_offense_12mo}
            onChange={(e) =>
              setForm({ ...form, first_offense_12mo: e.target.checked })
            }
          />
          <span>
            I have NOT elected traffic school in the past 12 months (required
            for school path)
          </span>
        </label>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          className="btn"
          onClick={onNext}
          disabled={!valid}
          style={{ opacity: valid ? 1 : 0.4 }}
        >
          NEXT →
        </button>
      </div>
    </section>
  );
}
