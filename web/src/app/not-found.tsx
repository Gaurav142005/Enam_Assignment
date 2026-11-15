import Link from "next/link";
import { SearchX } from "lucide-react";
import { Logo } from "@/components/Logo";

export default function NotFound() {
  return (
    <main className="px-4 pt-[calc(env(safe-area-inset-top)+0.75rem)]">
      <Logo />
      <div className="mt-16 flex flex-col items-center text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-tint-sky text-tint-sky-ink">
          <SearchX size={26} />
        </span>
        <h1 className="mt-4 font-display text-2xl font-semibold tracking-tight">Nothing here</h1>
        <p className="mt-2 max-w-xs text-[15px] leading-relaxed text-muted">
          That company or page doesn&apos;t exist. If you were looking for a stock, search by name or NSE ticker.
        </p>
        <div className="mt-6 flex gap-2">
          <Link href="/ask" className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-bg">
            Search companies
          </Link>
          <Link href="/" className="rounded-full border border-line bg-surface px-5 py-2.5 text-sm font-medium">
            Back to Brief
          </Link>
        </div>
      </div>
    </main>
  );
}
