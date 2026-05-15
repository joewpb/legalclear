import counties from "../../data/fl_counties.json";
import violations from "../../data/fl_traffic_violations.json";
import type { ChosenPath, County, TrafficForm, Violation } from "./types";

const COUNTIES = counties as County[];
const VIOLATIONS = violations as Violation[];

type Props = {
  form: TrafficForm;
  setForm: (f: TrafficForm) => void;
  onBack: () => void;
  onNext: () => void;
};

export default function OptionsStep({ form, setForm, onBack, onNext }: Props) {
  const v = VIOLATIONS.find((x) => x.type === form.citation_type);
  const isDui = form.citation_type === "DUI";

  // Available paths per spec:
  // - Pay: always available (admit guilt)
  // - Traffic school: civil + points-bearing + traffic_school_eligible + user attested first offense in 12 mo
  // - Contest: available unless DUI (DUI selection disables Contest path)
  const schoolAvailable = Boolean(
    v?.traffic_school_eligible && v.is_civil_infraction && form.first_offense_12mo,
  );
  const contestAvailable = !isDui;

  const valid = form.county.length > 0 && form.chosen_path.length > 0;

  function pick(p: ChosenPath) {
    setForm({ ...form, chosen_path: p });
  }

  return (
    <section style={{ padding: 32, display: "grid", gap: 16 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: 0 }}>
        Step 2 — County + resolution path
      </h2>

      <label>
        <span style={{ display: "block", color: "var(--muted)", marginBottom: 4 }}>
          County of citation *
        </span>
        <select
          className="input"
          value={form.county}
          onChange={(e) => setForm({ ...form, county: e.target.value })}
          style={{ width: "100%" }}
        >
          <option value="">— select —</option>
          {COUNTIES.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
      </label>

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
          DUI: Contest path is disabled in this wizard. Consult a licensed FL
          criminal-defense attorney before taking any action on a DUI charge.
        </p>
      )}

      <fieldset style={{ border: 0, padding: 0 }}>
        <legend style={{ color: "var(--muted)", marginBottom: 8 }}>
          How do you want to resolve this citation? *
        </legend>
        <div style={{ display: "grid", gap: 8 }}>
          <PathOption
            label="PAY"
            description="Admit responsibility and pay the citation. Points (if any) apply to your driving record."
            value="pay"
            chosen={form.chosen_path}
            disabled={false}
            onClick={() => pick("pay")}
          />
          <PathOption
            label="TRAFFIC SCHOOL"
            description={
              schoolAvailable
                ? "Elect Basic Driver Improvement (BDI) school — citation withheld from your record."
                : "Not available: this citation isn't traffic-school eligible (or you've already elected school in the past 12 months)."
            }
            value="school"
            chosen={form.chosen_path}
            disabled={!schoolAvailable}
            onClick={() => schoolAvailable && pick("school")}
          />
          <PathOption
            label="CONTEST"
            description={
              contestAvailable
                ? "Request a court hearing. You will appear before a judge or hearing officer."
                : "Not available for DUI in this wizard. Hire a criminal-defense attorney."
            }
            value="contest"
            chosen={form.chosen_path}
            disabled={!contestAvailable}
            onClick={() => contestAvailable && pick("contest")}
          />
        </div>
      </fieldset>

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button className="btn" onClick={onBack}>
          ← BACK
        </button>
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

function PathOption({
  label,
  description,
  value,
  chosen,
  disabled,
  onClick,
}: {
  label: string;
  description: string;
  value: ChosenPath;
  chosen: ChosenPath;
  disabled: boolean;
  onClick: () => void;
}) {
  const selected = chosen === value;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        textAlign: "left",
        background: selected ? "var(--accent)" : "var(--bg)",
        color: selected ? "var(--bg)" : "var(--fg)",
        border: "1px solid var(--border)",
        padding: 16,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.4 : 1,
        display: "grid",
        gap: 4,
        font: "inherit",
      }}
    >
      <span className="mono" style={{ fontSize: 16 }}>
        {label}
      </span>
      <span style={{ fontSize: 13 }}>{description}</span>
    </button>
  );
}
