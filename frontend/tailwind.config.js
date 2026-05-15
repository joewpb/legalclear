/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Mirrors the CSS-variable tokens in src/styles/theme.css.
        // Use either via Tailwind utility (bg-bg, text-fg, text-accent)
        // or directly as var(--bg) etc. in inline styles.
        bg: "#FAFAF7",
        fg: "#1A1A1A",
        accent: "#1E40AF",
        "accent-hover": "#1E3A8A",
        muted: "#6B6B66",
        border: "#E5E5E0",
        "border-strong": "#C7C7BF",
        danger: "#B91C1C",
        success: "#166534",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],
      },
      maxWidth: {
        prose: "680px",
        page: "1140px",
      },
      borderRadius: {
        DEFAULT: "4px",
      },
      boxShadow: {
        // The single elevation token. Apply sparingly — currently used
        // only by HubTile on hover.
        soft: "0 1px 2px rgba(26, 26, 26, 0.04)",
      },
    },
  },
  plugins: [],
}
