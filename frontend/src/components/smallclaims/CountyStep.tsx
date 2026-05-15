import { useMemo, useState } from "react";
import { useWizard } from "./WizardContext";
import countiesRaw from "../../data/fl_counties.json";

type County = {
  name: string;
  clerk_url: string;
  fee_tier_1: number;
  fee_tier_2: number;
  fee_tier_3: number;
  fee_tier_4: number;
};

const COUNTIES = countiesRaw as County[];

export default function CountyStep() {
  const { data, setField, next, back } = useWizard();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return COUNTIES;
    return COUNTIES.filter((c) => c.name.toLowerCase().includes(q));
  }, [query]);

  const valid = data.county.length > 0;

  return (
    <section style={{ padding: 32 }}>
      <h2 className="mono" style={{ fontSize: 20, margin: "0 0 16px" }}>
        Which Florida county?
      </h2>
      <input
        className="input"
        placeholder="Search counties…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "100%", marginBottom: 16 }}
        aria-label="Search counties"
      />
      <div
        style={{
          border: "1px solid var(--border)",
          maxHeight: 320,
          overflowY: "auto",
        }}
        role="listbox"
        aria-label="Florida counties"
      >
        {filtered.length === 0 && (
          <p style={{ padding: 12, color: "var(--muted)", margin: 0 }}>
            No counties match "{query}".
          </p>
        )}
        {filtered.map((c) => {
          const selected = data.county === c.name;
          return (
            <button
              key={c.name}
              role="option"
              aria-selected={selected}
              onClick={() => setField("county", c.name)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: 12,
                border: "0",
                borderBottom: "1px solid var(--border)",
                background: selected ? "var(--accent)" : "transparent",
                color: selected ? "var(--bg)" : "var(--fg)",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
              }}
            >
              {c.name}
            </button>
          );
        })}
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 8 }}>
        {COUNTIES.length} Florida counties.{" "}
        {data.county && <strong>Selected: {data.county}</strong>}
      </p>
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
