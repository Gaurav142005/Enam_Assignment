import Link from "next/link";

/** FINN's mark: an F on an indigo tile, with the accent dot that stands for "the signal, surfaced". */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <linearGradient id="finn-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6366F1" />
          <stop offset="1" stopColor="#3730A3" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#finn-g)" />
      <path d="M22 46V18h21M22 32h14" fill="none" stroke="#fff" strokeWidth="6.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="45" cy="44" r="5" fill="#FBBF24" />
    </svg>
  );
}

export function Logo() {
  return (
    <Link href="/" className="inline-flex items-center gap-2" aria-label="FINN home">
      <LogoMark />
      <span className="font-display text-[17px] font-bold tracking-[0.12em]">FINN</span>
    </Link>
  );
}
