/**
 * Logo components — v1 retheme.
 *
 * Two exports:
 *   - LogoWordmark : "legal clear" in Fraunces, lowercase, color-split
 *     ("legal" in --fg, "clear" in --accent). Optical kerning enabled.
 *   - LogoMark     : a thin vertical line bisecting a circle —
 *     suggesting "translation" / "clarity through a lens". Stroke uses
 *     currentColor so the consumer decides the colour.
 *
 * Both are pure SVG / inline text — no rasterised assets — so they
 * scale losslessly. For the deferred 1200x630 OG image task, the
 * same SVG can be rasterised via PIL or any headless browser path.
 */
import { CSSProperties } from "react";

type Props = {
  /** Pixel height of the wordmark / square edge of the mark. Default 24. */
  size?: number;
  className?: string;
  style?: CSSProperties;
};

export function LogoWordmark({ size = 24, className, style }: Props) {
  return (
    <span
      className={className}
      style={{
        display: "inline-block",
        fontFamily: "var(--font-serif)",
        fontWeight: 500,
        fontSize: size,
        lineHeight: 1,
        letterSpacing: "-0.02em",
        fontFeatureSettings: '"kern" 1, "liga" 1',
        ...style,
      }}
      aria-label="Legal Clear"
    >
      <span style={{ color: "var(--fg)" }}>legal</span>{" "}
      <span style={{ color: "var(--accent)" }}>clear</span>
    </span>
  );
}

export function LogoMark({ size = 24, className, style }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      role="img"
      aria-label="Legal Clear mark"
      className={className}
      style={style}
    >
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="2" x2="12" y2="22" />
    </svg>
  );
}

export default LogoWordmark;
