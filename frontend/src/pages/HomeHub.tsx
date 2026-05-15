import { Link } from "react-router-dom";
import HubTile from "../components/HubTile";

type Tile = { title: string; subtitle: string; to: string };

// 8 tiles, fixed order per phases/source/PHASE_15_hub_restructure.md.
// Titles flipped to sentence case as part of the v1 retheme.
const TILES: Tile[] = [
  {
    title: "I have a document",
    subtitle: "Upload and get a plain-English breakdown",
    to: "/upload",
  },
  {
    title: "Small claims (FL)",
    subtitle: "File a claim for up to $8,000 in Florida",
    to: "/small-claims",
  },
  {
    title: "Expungement (FL)",
    subtitle: "Seal or expunge a Florida record",
    to: "/expungement",
  },
  {
    title: "Landlord / tenant (FL)",
    subtitle: "Rent, deposits, eviction defense",
    to: "/landlord",
  },
  {
    title: "Court forms finder (FL)",
    subtitle: "Locate the correct FL forms for your case",
    to: "/forms",
  },
  {
    title: "Traffic / tickets (FL)",
    subtitle: "Contest or handle a Florida ticket",
    to: "/traffic",
  },
  {
    title: "Police report analyzer",
    subtitle: "Upload a report — find inconsistencies",
    to: "/police-report",
  },
  {
    title: "FL case law lookup",
    subtitle: "Search Florida case law via CourtListener",
    to: "/case-law",
  },
];

// v1 retheme — editorial layout:
//   - Asymmetric: hero block left-aligned at prose width (680px),
//     full-bleed grid below at page width (1140px).
//   - One serif headline (~36px), one sans body line, one immediate CTA.
//   - No marketing copy. Plain functional description.
//   - Site header / footer are global (rendered by App.tsx).
export default function HomeHub() {
  return (
    <>
      <section
        className="container"
        style={{
          paddingTop: "var(--space-8)",
          paddingBottom: "var(--space-6)",
        }}
      >
        <div className="prose">
          <h1
            style={{
              fontSize: 44,
              margin: "0 0 var(--space-2)",
              letterSpacing: "-0.025em",
              lineHeight: 1.1,
            }}
          >
            Florida legal help,{" "}
            <span style={{ color: "var(--accent)" }}>
              explained in plain English.
            </span>
          </h1>
          <p
            style={{
              fontSize: 18,
              lineHeight: 1.55,
              color: "var(--muted)",
              margin: "0 0 var(--space-4)",
            }}
          >
            Upload a document or pick a topic. Get a clear explanation, a
            filing packet, and the next step — for $0 to $35.
          </p>
          <Link
            to="/upload"
            className="btn"
            style={{ textDecoration: "none" }}
          >
            Get started
          </Link>
        </div>
      </section>

      <section
        className="container"
        style={{ paddingBottom: "var(--space-6)" }}
      >
        <h2
          className="mono"
          style={{
            color: "var(--muted)",
            margin: "0 0 var(--space-3)",
            fontSize: 12,
          }}
        >
          Pick a tool
        </h2>
        <div className="hub-grid">
          {TILES.map((t) => (
            <HubTile
              key={t.to}
              title={t.title}
              subtitle={t.subtitle}
              to={t.to}
            />
          ))}
        </div>
      </section>
    </>
  );
}
