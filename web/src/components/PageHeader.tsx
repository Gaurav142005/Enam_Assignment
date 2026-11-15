import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

/** Top-level pages get the FINN logo; detail pages (compact) have a back link instead. */
export function PageHeader({
  title,
  sub,
  right,
  compact,
  eyebrow,
  below,
}: {
  title: string;
  sub?: React.ReactNode;
  right?: React.ReactNode;
  compact?: boolean;
  eyebrow?: string;
  below?: React.ReactNode;
}) {
  const top = compact ? "pt-1" : "pt-[calc(env(safe-area-inset-top)+0.75rem)]";
  return (
    <header className={`sticky top-0 z-10 bg-bg/90 px-4 pb-3 ${top} backdrop-blur-md`}>
      {!compact && (
        <div className="mb-3 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-1">
            <ThemeToggle />
            {right}
          </div>
        </div>
      )}
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
          <h1 className="font-display text-[28px] font-semibold leading-tight tracking-tight">{title}</h1>
          {sub && <p className="mt-1 text-[15px] leading-snug text-muted">{sub}</p>}
        </div>
        {compact && right}
      </div>
      {below && <div className="mt-3">{below}</div>}
    </header>
  );
}

export function SectionTitle({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="mb-2.5 mt-7 flex items-baseline justify-between px-4">
      <h2 className="flex items-center gap-2 font-display text-[17px] font-semibold tracking-tight">
        <span className="h-4 w-1 rounded-full bg-marker" aria-hidden />
        {children}
      </h2>
      {right}
    </div>
  );
}
