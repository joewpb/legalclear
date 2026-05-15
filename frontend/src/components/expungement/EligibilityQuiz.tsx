import { useMemo, useState } from "react";
import disqualifiersRaw from "../../data/fl_disqualifying_offenses.json";

const DISQUALIFIERS = disqualifiersRaw as string[];

export type QuizAnswers = {
  disposition: string;
  charge: string;
  completed_terms: string;
  previously_sealed: string;
  years_since_closed: string;
};

export const EMPTY_ANSWERS: QuizAnswers = {
  disposition: "",
  charge: "",
  completed_terms: "",
  previously_sealed: "",
  years_since_closed: "",
};

const DISPOSITIONS = [
  "Dismissed",
  "Nolle prossed",
  "Adjudication withheld",
  "Adjudicated guilty",
  "Never charged",
];
const YES_NO_NA = ["Yes", "No", "N/A"];
const YES_NO = ["Yes", "No"];
const YEARS_BUCKETS = ["<1 yr", "1-5 yrs", "5-10 yrs", "10+ yrs"];

type Props = {
  onSubmit: (answers: QuizAnswers) => void;
  submitting: boolean;
};

function RadioRow({
  legend,
  options,
  value,
  onChange,
}: {
  legend: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <fieldset style={{ border: 0, padding: 0, marginBottom: 24 }}>
      <legend
        className="mono"
        style={{ marginBottom: 12, fontSize: 14, letterSpacing: "0.04em" }}
      >
        {legend}
      </legend>
      <div style={{ display: "grid", gap: 8 }}>
        {options.map((opt) => (
          <label
            key={opt}
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
              checked={value === opt}
              onChange={() => onChange(opt)}
            />
            <span>{opt}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function EligibilityQuiz({ onSubmit, submitting }: Props) {
  const [answers, setAnswers] = useState<QuizAnswers>(EMPTY_ANSWERS);

  const setField = <K extends keyof QuizAnswers>(k: K, v: QuizAnswers[K]) =>
    setAnswers((a) => ({ ...a, [k]: v }));

  const chargeMatches = useMemo(() => {
    const q = answers.charge.trim().toLowerCase();
    if (!q) return [];
    return DISQUALIFIERS.filter((d) => d.includes(q)).slice(0, 6);
  }, [answers.charge]);

  const complete =
    answers.disposition &&
    answers.charge.trim().length > 0 &&
    answers.completed_terms &&
    answers.previously_sealed &&
    answers.years_since_closed;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (complete) onSubmit(answers);
      }}
      style={{ padding: 32 }}
    >
      <RadioRow
        legend="1. What was the case disposition?"
        options={DISPOSITIONS}
        value={answers.disposition}
        onChange={(v) => setField("disposition", v)}
      />

      <div style={{ marginBottom: 24 }}>
        <label
          className="mono"
          style={{
            display: "block",
            marginBottom: 12,
            fontSize: 14,
            letterSpacing: "0.04em",
          }}
        >
          2. What was the charge?
        </label>
        <input
          className="input"
          value={answers.charge}
          onChange={(e) => setField("charge", e.target.value)}
          placeholder="e.g. Petit theft, DUI, etc."
          style={{ width: "100%" }}
          autoComplete="off"
          list="charge-suggestions"
        />
        <datalist id="charge-suggestions">
          {DISQUALIFIERS.map((d) => (
            <option key={d} value={d} />
          ))}
        </datalist>
        {chargeMatches.length > 0 && (
          <p
            style={{
              color: "var(--muted)",
              fontSize: 12,
              marginTop: 8,
              fontFamily: "var(--font-mono)",
            }}
          >
            Matches §943.0584 disqualifier list:{" "}
            {chargeMatches.join(", ")}
          </p>
        )}
      </div>

      <RadioRow
        legend="3. Have you completed all terms (probation, fees, restitution)?"
        options={YES_NO_NA}
        value={answers.completed_terms}
        onChange={(v) => setField("completed_terms", v)}
      />

      <RadioRow
        legend="4. Have you previously sealed or expunged any FL record?"
        options={YES_NO}
        value={answers.previously_sealed}
        onChange={(v) => setField("previously_sealed", v)}
      />

      <RadioRow
        legend="5. How long since the case closed?"
        options={YEARS_BUCKETS}
        value={answers.years_since_closed}
        onChange={(v) => setField("years_since_closed", v)}
      />

      <button
        type="submit"
        className="btn"
        disabled={!complete || submitting}
        style={{ opacity: !complete || submitting ? 0.4 : 1 }}
      >
        {submitting ? "CHECKING…" : "CHECK ELIGIBILITY"}
      </button>
    </form>
  );
}
