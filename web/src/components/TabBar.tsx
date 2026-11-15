"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BriefcaseBusiness, Inbox, Search, Waypoints } from "lucide-react";

const TABS = [
  { href: "/", label: "Brief", icon: Inbox, match: (p: string) => p === "/" || p.startsWith("/settings") },
  { href: "/portfolio", label: "Portfolio", icon: BriefcaseBusiness, match: (p: string) => p.startsWith("/portfolio") },
  { href: "/ask", label: "Ask", icon: Search, match: (p: string) => p.startsWith("/ask") || p.startsWith("/company") },
  { href: "/network", label: "Network", icon: Waypoints, match: (p: string) => p.startsWith("/network") || p.startsWith("/people") },
];

export function TabBar() {
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/90 backdrop-blur-md" aria-label="Main">
      <ul className="mx-auto grid max-w-app grid-cols-4 px-2 pb-[env(safe-area-inset-bottom)]">
        {TABS.map(({ href, label, icon: Icon, match }) => {
          const active = match(path);
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
