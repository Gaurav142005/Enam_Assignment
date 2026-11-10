import Link from "next/link";
import { pct, tone } from "@/lib/format";
import type { PushItem } from "@/lib/types";
import { CATEGORY_ICON } from "./PushCard";

/** What a line in the glance says: the fact, not the filing's wording. */
function line(i: PushItem): React.ReactNode {
  const r = i.results;
  if (r) {
    const rev = r.rows.find((x) => x.metric === "Revenue");
    const pat = r.rows.find((x) => x.metric === "PAT");
    return (
      <>
        {r.period} results: revenue <span className={`num font-medium ${tone(rev?.yoy_pct ?? null)}`}>{pct(rev?.yoy_pct ?? null)}</span>, PAT{" "}
        <span className={`num font-medium ${tone(pat?.yoy_pct ?? null)}`}>{pct(pat?.yoy_pct ?? null)}</span> YoY
      </>
    );
  }
  return i.title;
}

/**
 * The fast read: every card in the deck as one line, plus the day's moves. Built from the same ranked items as the
 * cards (no model, no wait). Tapping a line jumps to its card.
 */
export function Glance({ items, moves }: { items: PushItem[]; moves: PushItem[] }) {
  if (!items.length && !moves.length) return null;
  // One line per company: its highest-ranked item, with a count of the rest.
  const byCo = new Map<string, PushItem[]>();
  for (const i of items) byCo.set(i.ticker, [...(byCo.get(i.ticker) ?? []), i]);
  const rows = [...byCo.values()].slice(0, 8);
  return (
    <section className="card mx-4 p-4" aria-label="At a glance">
      <p className="eyebrow mb-2">At a glance</p>
      <ul className="space-y-2">
        {rows.map(([i, ...more]) => {
          const Icon = i.category ? CATEGORY_ICON[i.category] : CATEGORY_ICON.unclassified;
          return (
            <li key={i.id}>
              <a href={`#card-${i.id}`} className="flex gap-2.5 text-[13px] leading-snug active:opacity-60">
                <Icon size={15} className="mt-0.5 shrink-0 text-muted" aria-hidden />
                <span className="min-w-0 flex-1 line-clamp-2">
                  <span className="font-semibold">{i.ticker}</span> <span className="text-ink/80">{line(i)}</span>
                  {more.length > 0 && <span className="text-muted"> · +{more.length} more</span>}
                </span>
                {i.is_new ? (
                  <span className="shrink-0 self-start rounded-full bg-accent px-1.5 py-px text-[10px] font-semibold text-bg">New</span>
                ) : (
                  i.priority === "critical" && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-down" role="img" aria-label="Critical" />
                )}
              </a>
            </li>
          );
        })}
        {moves.map((m) => (
          <li key={m.id}>
            <Link href={`/company/${m.ticker}`} className="flex gap-2.5 text-[13px] leading-snug active:opacity-60">
              <span className={`num mt-px w-[15px] shrink-0 text-center text-[11px] font-bold ${tone(m.change_pct)}`} aria-hidden>
                {(m.change_pct ?? 0) >= 0 ? "▲" : "▼"}
              </span>
              <span className="min-w-0 flex-1 line-clamp-2">
                <span className="font-semibold">{m.ticker}</span> <span className={`num font-medium ${tone(m.change_pct)}`}>{pct(m.change_pct)}</span>
                <span className="text-ink/80">{m.kind === "volume_spike" ? ` on ${m.title.match(/[\d.]+×/)?.[0] ?? "high"} volume` : " on the day"}</span>
                {m.context && <span className="text-muted"> · {m.context.replace(/^Filed that session: /, "")}</span>}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
