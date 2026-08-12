import { useState } from "react";
import providers from "../data/fl_legal_aid_providers.json";
import publicDefenders from "../data/fl_public_defenders.json";

interface Provider {
  name: string;
  phone: string;
  website: string;
  areas_served: string;
  legal_issues: string;
  description: string;
}

export default function FindLegalHelpFL() {
  const [county, setCounty] = useState("");

  // Match providers by county search
  const filtered = county.trim()
    ? providers.filter((p: Provider) =>
        p.areas_served.toLowerCase().includes(county.toLowerCase())
      )
    : [];

  return (
    <main className="page" style={{ maxWidth: 720, margin: "0 auto", padding: "0 16px 32px" }}>
      <h1 style={{ fontFamily: "var(--font-serif)", fontSize: 24, margin: "16px 0 8px" }}>
        Find Free Legal Help in Florida
      </h1>
      <p style={{ color: "var(--muted)", fontSize: 14, marginBottom: 20, lineHeight: 1.6 }}>
        Free or low-cost legal help exists in every Florida county. Search below
        to find legal aid programs and the public defender office for your area.
      </p>

      {/* County search */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>
          Search by county
        </label>
        <input
          type="text"
          value={county}
          onChange={(e) => setCounty(e.target.value)}
          placeholder="e.g., St. Lucie, Duval, Broward..."
          style={{
            width: "100%",
            padding: "10px 12px",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 14,
            background: "var(--bg)",
            color: "var(--fg)",
          }}
        />
      </div>

      {/* Search results */}
      {county.trim() && (
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 17, marginBottom: 12 }}>
            Legal aid serving {county}
          </h2>
          {filtered.length === 0 ? (
            <div
              style={{
                padding: 14,
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 13,
                lineHeight: 1.5,
              }}
            >
              No legal aid program lists {county} specifically. Try the nearest
              program below, or call the Florida Bar referral line at{" "}
              <strong>800-342-8011</strong>.
            </div>
          ) : (
            filtered.map((p: Provider) => (
              <div
                key={p.name}
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: 14,
                  marginBottom: 10,
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 15 }}>{p.name}</div>
                {p.phone && (
                  <div style={{ fontSize: 14, margin: "4px 0" }}>
                    📞 {p.phone}
                  </div>
                )}
                {p.legal_issues && (
                  <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 6 }}>
                    Helps with: {p.legal_issues}
                  </div>
                )}
                {p.description && (
                  <div style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>
                    {p.description}
                  </div>
                )}
                {p.website && (
                  <a
                    href={`https://${p.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 13, color: "var(--accent)" }}
                  >
                    Apply online →
                  </a>
                )}
              </div>
            ))
          )}
        </section>
      )}

      {/* Public defenders */}
      <section>
        <h2 style={{ fontSize: 17, marginBottom: 12 }}>
          Public Defenders by Circuit
        </h2>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 12, lineHeight: 1.5 }}>
          If you've been arrested and cannot afford a lawyer, the court can
          appoint a public defender. Find your circuit below.
        </p>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 13,
          }}
        >
          <thead>
            <tr>
              <th style={thStyle}>Circuit</th>
              <th style={thStyle}>Counties</th>
              <th style={thStyle}>Website</th>
            </tr>
          </thead>
          <tbody>
            {publicDefenders.map((pd: any) => (
              <tr key={pd.circuit}>
                <td style={tdStyle}>{pd.circuit}</td>
                <td style={tdStyle}>{pd.counties}</td>
                <td style={tdStyle}>
                  {pd.site ? (
                    <a
                      href={`https://${pd.site}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--accent)" }}
                    >
                      Visit →
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Statewide hotlines */}
      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: 17, marginBottom: 12 }}>Statewide Hotlines</h2>
        <div style={{ fontSize: 14, lineHeight: 2 }}>
          <div>📞 Florida Bar Lawyer Referral: <strong>800-342-8011</strong></div>
          <div>📞 Florida Domestic Violence Hotline: <strong>800-500-1119</strong></div>
          <div>📞 Florida Senior Legal Helpline: <strong>888-895-7873</strong></div>
          <div>📞 Florida Veterans Legal Helpline: <strong>866-486-6161</strong></div>
          <div>📞 Florida Disaster Legal Aid: <strong>833-514-2940</strong></div>
          <div>📞 Eviction Prevention Line: <strong>888-780-0443</strong></div>
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          marginTop: 28,
          padding: 20,
          border: "1px solid var(--border)",
          borderRadius: 8,
          background: "var(--bg-muted)",
        }}
      >
        <h2 style={{ fontSize: 17, marginBottom: 8 }}>
          Need a private attorney instead?
        </h2>
        <p style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 12 }}>
          Tell us about your case and we'll connect you with a Florida attorney.
          Free, confidential, no obligation.
        </p>
        <a
          href="/attorney-referral"
          style={{
            display: "inline-block",
            padding: "10px 20px",
            background: "var(--accent)",
            color: "#fff",
            borderRadius: 8,
            fontWeight: 600,
            textDecoration: "none",
            fontSize: 14,
          }}
        >
          Get Matched with an Attorney
        </a>
      </section>
    </main>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px",
  borderBottom: "2px solid var(--border)",
  fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: "8px",
  borderBottom: "1px solid var(--border)",
  verticalAlign: "top",
};
