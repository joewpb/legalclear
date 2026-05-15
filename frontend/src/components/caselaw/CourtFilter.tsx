import { COURT_FILTERS } from "./types";
import type { CourtFilterValue } from "./types";

type Props = {
  value: CourtFilterValue;
  onChange: (v: CourtFilterValue) => void;
};

export default function CourtFilter({ value, onChange }: Props) {
  return (
    <label style={{ display: "grid", gap: 8 }}>
      <span
        className="mono"
        style={{
          fontSize: 12,
          color: "var(--muted)",
          letterSpacing: "0.08em",
        }}
      >
        COURT FILTER
      </span>
      <select
        className="input mono"
        value={value}
        onChange={(e) => onChange(e.target.value as CourtFilterValue)}
        style={{
          padding: "10px 12px",
          fontSize: 14,
          border: "2px solid var(--border-strong)",
        }}
      >
        {COURT_FILTERS.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label}
          </option>
        ))}
      </select>
    </label>
  );
}
