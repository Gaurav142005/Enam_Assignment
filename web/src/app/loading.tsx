/** Shared skeleton: holds the layout steady while a page's data loads. */
export default function Loading() {
  return (
    <main className="animate-pulse px-4 pt-[calc(env(safe-area-inset-top)+1.5rem)]" aria-busy="true" aria-label="Loading">
      <div className="h-3 w-28 rounded bg-line" />
      <div className="mt-2 h-7 w-40 rounded bg-line" />
      <div className="mt-2 h-4 w-64 rounded bg-line" />
      <div className="mt-6 h-44 rounded-2xl bg-line/70" />
      <div className="mt-3 h-24 rounded-2xl bg-line/70" />
      <div className="mt-3 h-24 rounded-2xl bg-line/70" />
    </main>
  );
}
