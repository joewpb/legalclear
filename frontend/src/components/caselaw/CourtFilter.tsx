import { useState } from "react";
import { COURT_FILTERS } from "./types";
import type { CourtFilterValue } from "./types";

type Props = {
  value: CourtFilterValue;
  onChange: (v: CourtFilterValue) => void;
};

export default function CourtFilter({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "none",
          border: "none",
          padding: 0,
          cursor: "pointer",
          fontSize: 14,
          fontWeight: 500,
          color: "var(--fg)",
          fontFamily: "var(--font-sans)",
        }}
      >
        <span>Filter by court</span>
        <span
          style={{
            fontSize: 10,
            color: "var(--muted)",
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 150ms ease",
          }}
        >
          ▼
        </span>
      </button>

      {open && (
        <div
          style={{
            display: "grid",
            gap: 10,
            padding: "14px 16px",
            border: "1px solid var(--border)",
            background: "#FFFFFF",
          }}
        >
          <p
            style={{
              fontSize: 12,
              color: "var(--muted)",
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            Most people should leave this on <strong>All Florida courts</strong>.
            Filtering is useful when you already know which court level produced
            the decision you need.
          </p>
          <select
            className="input"
            value={value}
            onChange={(e) => onChange(e.target.value as CourtFilterValue)}
            style={{
              padding: "10px 12px",
              fontSize: 14,
              border: "2px solid var(--border-strong)",
            }}
          >
            {COURT_FILTERS.map((f) => (
              <option key={f.value} value={f.value} title={f.description}>
                {f.label}
              </option>
            ))}
          </select>
          {COURT_FILTERS.filter((f) => f.value !== "all").map((f) => (
            <p
              key={f.value}
              style={{
                fontSize: 12,
                color: "var(--muted)",
                margin: 0,
                lineHeight: 1.4,
              }}
            >
              <strong>{f.label}:</strong> {f.description}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
