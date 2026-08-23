/**
 * I-9 — persistent, non-dismissible disclaimer (2026-08-23).
 *
 * Spec §9.3: a persistent disclaimer on every phase screen — NOT a
 * one-time modal at signup. This strip renders on the Claim Guide page and
 * cannot be dismissed; it carries the canonical DISCLAIMER_TEXT (backend
 * mirror) and the free-help link.
 */

import { Link } from "react-router-dom";
import { DISCLAIMER_TEXT } from "./DisclaimerNote";

export default function PersistentDisclaimer({ compact }: { compact?: boolean }) {
  return (
    <div
      role="note"
      aria-label="Legal disclaimer"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        borderTop: "2px solid var(--border-strong)",
        background: "#F7F7F4",
        padding: "var(--space-2)",
        fontSize: 12,
        lineHeight: 1.6,
        color: "var(--muted)",
        marginTop: "var(--space-3)",
      }}
    >
      <p style={{ margin: 0 }}>{DISCLAIMER_TEXT}</p>
      {!compact && (
        <Link
          to="/find-legal-help"
          style={{ fontSize: 12, textDecoration: "underline", color: "var(--accent)" }}
        >
          Find free legal help
        </Link>
      )}
    </div>
  );
}
