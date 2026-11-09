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
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/85 backdrop-blur-md">
      <ul className="mx-auto flex max-w-app justify-around px-4 pb-[env(safe-area-inset-bottom)]">
        {TABS.map(({ href, label, icon: Icon, match }) => {
          const active = match(path);
          return (
            <li key={href}>
              <Link
                href={href}
                className={`flex h-16 w-[4.5rem] flex-col items-center justify-center gap-1 text-[11px] font-medium ${active ? "text-ink" : "text-muted"}`}
              >
                <Icon size={21} strokeWidth={active ? 2.2 : 1.7} />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
