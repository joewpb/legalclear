import { LogoWordmark } from "./Logo";

/**
 * Site-wide footer. Rendered once in App.tsx below <Routes>.
 *
 * Layout: wordmark at 16px above the two-paragraph disclaimer.
 * Disclaimer is set in 14px / 1.6 line-height per the retheme spec —
 * "Legal Clear is not a law firm. We provide educational explanations
 * only." sits in a readable size, not buried fine print.
 */
export default function SiteFooter() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg)",
        marginTop: "var(--space-8)",
      }}
    >
      <div
        className="container"
        style={{
          paddingTop: "var(--space-4)",
          paddingBottom: "var(--space-4)",
          display: "grid",
          gap: "var(--space-2)",
          maxWidth: "var(--max-prose)",
          paddingLeft: 24,
          paddingRight: 24,
        }}
      >
        <LogoWordmark size={16} />
        <p
          style={{
            margin: 0,
            fontSize: 14,
            lineHeight: 1.6,
            color: "var(--fg)",
          }}
        >
          Legal Clear is not a law firm. We provide educational explanations only.
        </p>
        <p
          style={{
            margin: 0,
            fontSize: 14,
            lineHeight: 1.6,
            color: "var(--muted)",
          }}
        >
          Nothing on this site is legal advice. Using it does not create an
          attorney-client relationship. For your specific situation, consult a
          licensed Florida attorney.
        </p>
      </div>
    </footer>
  );
}
