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
    },
  },
  plugins: [],
} satisfies Config;
