export function PageHeader({ title, sub, right, compact }: { title: string; sub?: React.ReactNode; right?: React.ReactNode; compact?: boolean }) {
  const top = compact ? "pt-1" : "pt-[calc(env(safe-area-inset-top)+1rem)]";
  return (
    <header className={`sticky top-0 z-10 bg-bg/90 px-4 pb-3 ${top} backdrop-blur-md`}>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight">{title}</h1>
          {sub && <p className="mt-0.5 text-sm text-muted">{sub}</p>}
        </div>
        {right}
      </div>
    </header>
  );
}

export function SectionTitle({ children, right }: { children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="mb-2 mt-6 flex items-baseline justify-between px-4">
      <h2 className="eyebrow">{children}</h2>
      {right}
    </div>
  );
}
