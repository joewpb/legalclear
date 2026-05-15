import { useState } from "react";

type Props = {
  initial: string;
  onSearch: (q: string) => void;
  submitting: boolean;
};

export default function SearchBar({ initial, onSearch, submitting }: Props) {
  const [q, setQ] = useState(initial);

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = q.trim();
    if (trimmed.length === 0) return;
    onSearch(trimmed);
  }

  return (
    <form
      onSubmit={submit}
      style={{ display: "grid", gap: 8, width: "100%" }}
    >
      <label
        className="mono"
        style={{
          fontSize: 12,
          color: "var(--muted)",
          letterSpacing: "0.08em",
        }}
      >
        SEARCH FL CASE LAW
      </label>
      <input
        className="input mono"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="e.g. stand your ground self defense"
        style={{
          width: "100%",
          padding: "12px 16px",
          fontSize: 16,
          border: "2px solid var(--border-strong)",
        }}
      />
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          type="submit"
          className="btn"
          disabled={submitting || q.trim().length === 0}
          style={{
            opacity: submitting || q.trim().length === 0 ? 0.4 : 1,
            padding: "10px 20px",
          }}
        >
          {submitting ? "SEARCHING…" : "SEARCH"}
        </button>
      </div>
    </form>
  );
}
