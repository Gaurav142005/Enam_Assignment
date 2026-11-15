const TINTS = [
  "bg-tint-mint text-tint-mint-ink",
  "bg-tint-peach text-tint-peach-ink",
  "bg-tint-sky text-tint-sky-ink",
  "bg-tint-lilac text-tint-lilac-ink",
];

/** Monogram tile for a company. The pastel is stable per ticker (decoration, not meaning), so lists are easier to scan. */
export function TickerBadge({ ticker, size = 36 }: { ticker: string; size?: number }) {
  const letters = ticker.replace(/[^A-Z]/g, "").slice(0, 2) || ticker.slice(0, 2);
  const tint = TINTS[[...ticker].reduce((n, ch) => n + ch.charCodeAt(0), 0) % TINTS.length];
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-xl font-display font-bold tracking-tight ${tint}`}
      style={{ width: size, height: size, fontSize: size * 0.34 }}
      aria-hidden
    >
      {letters}
    </span>
  );
}
