export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="px-4 py-8 text-center text-sm text-muted">{children}</p>;
}

export function DemoNote() {
  return (
    <p className="mx-4 mt-8 text-center text-[11px] text-muted">
      Demo data: announcements and network profiles are synthetic until the live feeds are wired.
    </p>
  );
}
