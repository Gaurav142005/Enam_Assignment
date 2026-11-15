import type { Config } from "tailwindcss";

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        ink: v("ink"),
        muted: v("muted"),
        line: v("line"),
        accent: v("accent"),
        "accent-soft": v("accent-soft"),
        up: v("up"),
        down: v("down"),
        "up-ink": v("up-ink"),
        "tint-peach": v("tint-peach"),
        "tint-mint": v("tint-mint"),
        "tint-sky": v("tint-sky"),
        "tint-lilac": v("tint-lilac"),
        "tint-peach-ink": v("tint-peach-ink"),
        "tint-mint-ink": v("tint-mint-ink"),
        "tint-sky-ink": v("tint-sky-ink"),
        "tint-lilac-ink": v("tint-lilac-ink"),
        marker: v("marker"),
        "down-ink": v("down-ink"),
        warn: v("warn"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
      },
      maxWidth: { app: "30rem" },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "sheet-up": { from: { transform: "translateY(24px)", opacity: "0" }, to: { transform: "none", opacity: "1" } },
        rise: { from: { transform: "translateY(6px)", opacity: "0" }, to: { transform: "none", opacity: "1" } },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out both",
        "sheet-up": "sheet-up 320ms cubic-bezier(0.2, 0.8, 0.2, 1) both",
        rise: "rise 260ms cubic-bezier(0.2, 0.8, 0.2, 1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;
