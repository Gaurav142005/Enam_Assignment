/** Monogram tile for a company: quiet, consistent, no fake logos. */
export function TickerBadge({ ticker, size = 36 }: { ticker: string; size?: number }) {
  const letters = ticker.replace(/[^A-Z]/g, "").slice(0, 2) || ticker.slice(0, 2);
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-xl border border-line bg-bg font-semibold tracking-tight text-ink"
      style={{ width: size, height: size, fontSize: size * 0.34 }}
      aria-hidden
    >
      {letters}
    </span>
  );
}
