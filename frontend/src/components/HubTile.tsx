import { Link } from "react-router-dom";

export type HubTileProps = {
  title: string;
  subtitle: string;
  to: string;
};

/**
 * Hub tile — used by HomeHub. v1 retheme:
 *   - Title is an <h3> (h2 belongs to the section heading "Pick a tool").
 *   - Sentence-case title rendering — no SHOUTCASE.
 *   - Hover/focus state lifts the tile with --shadow-soft (the only
 *     elevation in the app, per locked design constraint).
 */
export default function HubTile({ title, subtitle, to }: HubTileProps) {
  return (
    <Link to={to} className="hub-tile" aria-label={`${title}. ${subtitle}.`}>
      <h3 className="hub-tile__title">{title}</h3>
      <p className="hub-tile__subtitle">{subtitle}</p>
    </Link>
  );
}
