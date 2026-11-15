/** Page title in the display serif with an accent full stop; an optional tagline; and a slot for tabs that stick with it. */
export function PageHeader({
  title,
  sub,
  right,
  compact,
  eyebrow,
  below,
  dot = true,
}: {
  title: string;
  sub?: React.ReactNode;
  right?: React.ReactNode;
  compact?: boolean;
  eyebrow?: string;
  below?: React.ReactNode;
  dot?: boolean;
}) {
  const top = compact ? "pt-1" : "pt-[calc(env(safe-area-inset-top)+1.1rem)]";
  return (
    <header className={`sticky top-0 z-10 bg-bg/90 px-4 pb-3 ${top} backdrop-blur-md`}>
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
          <h1 className="font-display text-[32px] font-medium leading-[1.05] tracking-tight">
            {title}
            {dot && <span className="text-accent">.</span>}
          </h1>
          {sub && <p className="mt-1.5 font-display text-[17px] leading-snug text-ink/80">{sub}</p>}
        </div>
        {right}
      </div>
      {below && <div className="mt-3">{below}</div>}
    </header>
  );
}

export function SectionTitle({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="mb-2.5 mt-7 flex items-baseline justify-between px-4">
      <h2 className="eyebrow text-accent">{children}</h2>
      {right}
    </div>
  );
}
