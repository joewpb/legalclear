import { Link } from "react-router-dom";
import { LogoWordmark } from "./Logo";

/**
 * Site-wide header. Rendered once in App.tsx above <Routes>, so the
 * wordmark sits at the top-left of every page and routes to "/".
 *
 * Single horizontal rule (bottom border) separates from page content.
 * Padding follows the 8px vertical rhythm — 24px sides, 16px stack.
 */
export default function SiteHeader() {
  return (
    <header
      style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--bg)",
      }}
    >
      <div
        className="container"
        style={{
          display: "flex",
          alignItems: "center",
          paddingTop: "var(--space-2)",
          paddingBottom: "var(--space-2)",
        }}
      >
        <Link
          to="/"
          aria-label="Legal Clear — home"
          style={{ display: "inline-flex", alignItems: "center", textDecoration: "none" }}
        >
          <LogoWordmark size={24} />
        </Link>
      </div>
    </header>
  );
}
