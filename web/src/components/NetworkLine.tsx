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
        <span className="font-medium">
          {lead} {hint.name}
        </span>
        {hint.degree === 2 && hint.via && <span className="text-muted"> via {hint.via}</span>}
        <span className="block truncate text-muted">{hint.reason}</span>
      </span>
      <ChevronRight size={16} className="shrink-0 text-muted" />
    </Link>
  );
}
