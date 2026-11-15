"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BriefcaseBusiness, Inbox, Search, Waypoints } from "lucide-react";

const TABS = [
  { href: "/", label: "Brief", icon: Inbox, match: (p: string) => p === "/" || p.startsWith("/settings") },
  { href: "/portfolio", label: "Portfolio", icon: BriefcaseBusiness, match: (p: string) => p.startsWith("/portfolio") },
  { href: "/ask", label: "Ask", icon: Search, match: (p: string) => p.startsWith("/ask") },
  { href: "/network", label: "Network", icon: Waypoints, match: (p: string) => p.startsWith("/network") },
];

// Company and person pages open from every tab, so they keep lit the tab you came from.
const DETAIL_DEFAULT: [string, string][] = [["/company", "/ask"], ["/people", "/network"]];
const KEY = "finn.lastTab";

export function TabBar() {
  const pathname = usePathname();
  const own = TABS.find((t) => t.match(pathname));
  const [last, setLast] = useState<string | null>(null);
  useEffect(() => {
    if (own) {
      setLast(own.href);
      try {
        sessionStorage.setItem(KEY, own.href);
      } catch {}
    } else {
      try {
        setLast(sessionStorage.getItem(KEY));
      } catch {}
    }
  }, [own]);
  const path = own ? pathname : (last ?? DETAIL_DEFAULT.find(([pre]) => pathname.startsWith(pre))?.[1] ?? pathname);
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/90 backdrop-blur-md" aria-label="Main">
      <ul className="mx-auto grid max-w-app grid-cols-4 px-2 pb-[env(safe-area-inset-bottom)]">
        {TABS.map(({ href, label, icon: Icon, match }) => {
          const active = path === href || match(path);
          return (
            <li key={href}>
              <Link href={href} aria-current={active ? "page" : undefined} className="flex h-16 flex-col items-center justify-center gap-1">
                <span className={`flex h-8 w-14 items-center justify-center rounded-full transition-colors ${active ? "bg-accent-soft text-accent" : "text-muted"}`}>
                  <Icon size={20} strokeWidth={active ? 2.3 : 1.8} />
                </span>
                <span className={`text-[12px] ${active ? "font-semibold text-accent" : "text-muted"}`}>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
