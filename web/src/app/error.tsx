"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="flex min-h-[70dvh] flex-col items-center justify-center gap-3 px-8 text-center">
      <p className="text-[15px] font-medium">Couldn&apos;t load this</p>
      <p className="text-sm text-muted">{error.message}</p>
      <button onClick={reset} className="mt-2 rounded-full bg-ink px-4 py-2 text-sm text-bg">
        Try again
      </button>
    </main>
  );
}
