import { Link } from "react-router-dom";

export type HubTileProps = {
  title: string;
  subtitle: string;
  to: string;
  icon?: string;
};

const S = {
  tile: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 8,
    background: "#fff",
    border: "1px solid #E0E7FF",
    borderRadius: 16,
    padding: 20,
    textDecoration: "none",
    boxShadow: "0 2px 12px rgba(67,97,238,0.07)",
    transition: "box-shadow 0.2s, transform 0.2s",
  } as React.CSSProperties,

  icon: {
    fontSize: 24,
    lineHeight: 1,
  } as React.CSSProperties,

  title: {
    fontFamily: "var(--font-sans)",
    fontSize: 16,
    fontWeight: 600,
    color: "#1a1a2e",
    lineHeight: 1.2,
    margin: 0,
  } as React.CSSProperties,

  subtitle: {
    fontFamily: "var(--font-sans)",
    fontSize: 13,
    color: "#6B7280",
    lineHeight: 1.4,
    margin: 0,
  } as React.CSSProperties,
};

export default function HubTile({ title, subtitle, to, icon }: HubTileProps) {
  return (
    <Link
      to={to}
      style={S.tile}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow =
          "0 8px 24px rgba(67,97,238,0.15)";
        (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow =
          "0 2px 12px rgba(67,97,238,0.07)";
        (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
      }}
      aria-label={`${title}. ${subtitle}.`}
    >
      {icon && <span style={S.icon}>{icon}</span>}
      <h3 style={S.title}>{title}</h3>
      <p style={S.subtitle}>{subtitle}</p>
    </Link>
  );
}
