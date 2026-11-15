"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Brief", hint: "what changed", match: (p: string) => p === "/" || p.startsWith("/settings") },
  { href: "/portfolio", label: "Portfolio", hint: "what you hold", match: (p: string) => p.startsWith("/portfolio") },
  { href: "/ask", label: "Ask", hint: "dig in", match: (p: string) => p.startsWith("/ask") || p.startsWith("/company") },
  { href: "/network", label: "Network", hint: "who knows", match: (p: string) => p.startsWith("/network") || p.startsWith("/people") },
];

/** Words, not icons: each tab says what it's for. */
export function TabBar() {
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/90 backdrop-blur-md" aria-label="Main">
      <ul className="mx-auto grid max-w-app grid-cols-4 px-2 pb-[env(safe-area-inset-bottom)]">
        {TABS.map(({ href, label, hint, match }) => {
          const active = match(path);
          return (
            <li key={href}>
              <Link href={href} aria-current={active ? "page" : undefined} className="flex h-16 flex-col items-center justify-center">
                <span className={`font-display text-[19px] leading-tight ${active ? "font-semibold text-ink" : "text-muted"}`}>{label}</span>
                <span className={`text-[12px] ${active ? "text-ink/70" : "text-muted/80"}`}>{hint}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
