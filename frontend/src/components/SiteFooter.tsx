/**
 * Site-wide footer — glossy v3 restyle.
 * White background, #E0E7FF border-top, proper padding.
 */

export default function SiteFooter() {
  return (
    <footer
      style={{
        borderTop: "1px solid #E0E7FF",
        background: "#fff",
        marginTop: 0,
      }}
    >
      <div
        style={{
          maxWidth: 800,
          margin: "0 auto",
          padding: "32px 48px",
        }}
      >
        {/* Wordmark — matches header */}
        <p
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 16,
            fontWeight: 600,
            margin: "0 0 12px",
            lineHeight: 1.2,
          }}
        >
          <span style={{ color: "#1a1a2e" }}>legal</span>
          <span style={{ color: "#4361EE" }}>clear</span>
        </p>

        <p
          style={{
            margin: 0,
            fontSize: 13,
            lineHeight: 1.7,
            color: "#6B7280",
          }}
        >
          Legal Clear is not a law firm. We provide educational explanations
          only.
        </p>

        <p
          style={{
            margin: "6px 0 0",
            fontSize: 13,
            lineHeight: 1.7,
            color: "#6B7280",
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
