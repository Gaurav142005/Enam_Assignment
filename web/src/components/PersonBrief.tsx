import Link from "next/link";
import { tenure } from "@/lib/format";
import type { Person } from "@/lib/types";
import { Avatar } from "./Avatar";

/** Management change → who is this person and where did they come from. */
export function PersonBrief({ p }: { p: Person }) {
  const past = p.positions.slice(1, 3);  // [0] is the role they're taking now (shown in the card title)
  const edu = p.education[0];
  return (
    <Link href={`/people/${p.id}`} className="flex gap-3 rounded-xl border border-line p-3 active:opacity-70">
      <Avatar name={p.name} size={36} />
      <div className="min-w-0 text-[13px] leading-snug">
        <p className="font-medium">{p.name}</p>
        {past.map((pos) => (
          <p key={pos.company} className="text-muted">
            {[pos.title, pos.company].filter(Boolean).join(", ")}
            {pos.start !== null && ` · ${tenure(pos.start, pos.end)}`}
          </p>
        ))}
        {edu && (
          <p className="text-muted">
            {edu.school}
            {edu.end !== null && ` · ${edu.end}`}
          </p>
        )}
      </div>
    </Link>
  );
}
