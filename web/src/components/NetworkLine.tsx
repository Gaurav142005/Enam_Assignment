import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { NetworkHint } from "@/lib/types";
import { Avatar } from "./Avatar";

/** The weave: "who in my network can help me understand this", shown inline on Push and Pull. */
export function NetworkLine({ hint, lead = "Ask" }: { hint: NetworkHint; lead?: string }) {
  return (
    <Link
      href={`/people/${hint.person_id}`}
      className="flex items-center gap-3 rounded-xl bg-accent-soft/60 px-3 py-2.5 active:opacity-70"
    >
      <Avatar name={hint.name} size={28} />
      <span className="min-w-0 flex-1 text-[13px] leading-snug">
        <span className="font-medium">{[lead, hint.name].filter(Boolean).join(" ")}</span>
        {hint.relation === "peer" && <span className="ml-1.5 rounded-full bg-line px-1.5 py-px text-[10px] text-muted">competitor</span>}
        {hint.relation === "expert" && <span className="ml-1.5 rounded-full bg-line px-1.5 py-px text-[10px] text-muted">sector expert</span>}
        {hint.degree === 2 && hint.via && <span className="text-muted"> via {hint.via}</span>}
        <span className="block text-muted line-clamp-2">{hint.reason}</span>
      </span>
      <Strength value={hint.strength} />
      <ChevronRight size={16} className="shrink-0 text-muted" />
    </Link>
  );
}

/** How warm the link is: three bars, labelled for screen readers (never colour alone). */
export function Strength({ value }: { value: number }) {
  const level = value >= 0.7 ? 3 : value >= 0.45 ? 2 : 1;
  const label = ["", "Weak", "Medium", "Strong"][level];
  return (
    <span className="flex shrink-0 items-end gap-0.5" role="img" aria-label={`${label} connection`} title={`${label} connection`}>
      {[1, 2, 3].map((b) => (
        <span key={b} className={`w-1 rounded-full ${b <= level ? "bg-accent" : "bg-line"}`} style={{ height: 4 + b * 3 }} />
      ))}
    </span>
  );
}
