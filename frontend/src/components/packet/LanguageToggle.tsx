import { useEffect } from "react";

export type Language = "en" | "es";

const STORAGE_KEY = "lc.lang";

export function readLanguage(): Language {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "es" ? "es" : "en";
  } catch {
    return "en";
  }
}

export function writeLanguage(lang: Language) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* ignore */
  }
}

type Props = {
  value: Language;
  onChange: (lang: Language) => void;
};

export default function LanguageToggle({ value, onChange }: Props) {
  // Persist on every change so wizard pages can pick up the user's choice
  // before submitting their /generate request.
  useEffect(() => {
    writeLanguage(value);
  }, [value]);

  return (
    <div
      role="group"
      aria-label="Language"
      style={{ display: "inline-flex", border: "1px solid var(--border-strong)" }}
    >
      {(["en", "es"] as Language[]).map((l) => {
        const active = value === l;
        return (
          <button
            key={l}
            type="button"
            onClick={() => onChange(l)}
            className="mono"
            style={{
              padding: "6px 12px",
              fontSize: 12,
              letterSpacing: "0.08em",
              background: active ? "var(--accent)" : "transparent",
              color: active ? "#000" : "var(--muted)",
              border: "none",
              cursor: "pointer",
            }}
          >
            {l.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
