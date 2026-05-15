import HubTile from "../components/HubTile";

type Tile = { title: string; subtitle: string; to: string };

// 8 tiles, fixed order per phases/source/PHASE_15_hub_restructure.md.
const TILES: Tile[] = [
  {
    title: "I HAVE A DOCUMENT",
    subtitle: "Upload and get a plain-English breakdown",
    to: "/upload",
  },
  {
    title: "SMALL CLAIMS (FL)",
    subtitle: "File a claim for up to $8,000 in Florida",
    to: "/small-claims",
  },
  {
    title: "EXPUNGEMENT (FL)",
    subtitle: "Seal or expunge a Florida record",
    to: "/expungement",
  },
  {
    title: "LANDLORD / TENANT (FL)",
    subtitle: "Rent, deposits, eviction defense",
    to: "/landlord",
  },
  {
    title: "COURT FORMS FINDER (FL)",
    subtitle: "Locate the correct FL forms for your case",
    to: "/forms",
  },
  {
    title: "TRAFFIC / TICKETS (FL)",
    subtitle: "Contest or handle a Florida ticket",
    to: "/traffic",
  },
  {
    title: "POLICE REPORT ANALYZER",
    subtitle: "Upload a report — find inconsistencies",
    to: "/police-report",
  },
  {
    title: "FL CASE LAW LOOKUP",
    subtitle: "Search Florida case law via CourtListener",
    to: "/case-law",
  },
];

export default function HomeHub() {
  return (
    <>
      <header className="hub-header">
        <h1>LEGALCLEAR</h1>
        <p>Florida legal help, explained in plain English.</p>
      </header>
      <main className="hub-main">
        <section className="hub-grid">
          {TILES.map((t) => (
            <HubTile
              key={t.to}
              title={t.title}
              subtitle={t.subtitle}
              to={t.to}
            />
          ))}
        </section>
      </main>
      <footer className="page-disclaimer">
        <p>
          LegalClear provides informational tools only. Nothing here is legal
          advice. Using this site does not create an attorney-client
          relationship. For your specific situation, consult a licensed Florida
          attorney.
        </p>
      </footer>
    </>
  );
}
