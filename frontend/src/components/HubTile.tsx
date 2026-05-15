import { Link } from "react-router-dom";

export type HubTileProps = {
  title: string;
  subtitle: string;
  to: string;
};

export default function HubTile({ title, subtitle, to }: HubTileProps) {
  return (
    <Link to={to} className="hub-tile" aria-label={`${title}. ${subtitle}.`}>
      <h2 className="hub-tile__title">{title}</h2>
      <p className="hub-tile__subtitle">{subtitle}</p>
    </Link>
  );
}
