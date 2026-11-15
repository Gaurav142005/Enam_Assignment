import Link from "next/link";
import { Activity, ArrowUpRight, TrendingDown, TrendingUp } from "lucide-react";
import { pct, tone } from "@/lib/format";
import type { PushItem } from "@/lib/types";
import { TickerBadge } from "./TickerBadge";

export { CATEGORY_ICON } from "./categoryIcons";
export { BriefCard as PushCard } from "./BriefCard";

/** EOD trigger: the move is the headline, the likely reason sits right under it. */
export function MoveRow({ item }: { item: PushItem }) {
  const up = (item.change_pct ?? 0) >= 0;
  const vol = item.kind === "volume_spike";
  const Icon = vol ? Activity : up ? TrendingUp : TrendingDown;
  const [lead] = item.network;
  return (
    <div className="px-4 py-3">
      <Link href={`/company/${item.ticker}`} className="flex items-center gap-3 active:opacity-70">
        <TickerBadge ticker={item.ticker} size={34} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm font-semibold">
            {item.ticker}
            {item.is_new && <span className="rounded-full bg-accent px-1.5 py-px text-[11px] font-semibold text-bg">New</span>}
          </span>
          <span className="flex items-center gap-1 text-xs text-muted">
            <Icon size={13} className={vol ? "text-warn" : up ? "text-up-ink" : "text-down-ink"} aria-hidden />
            {item.title.replace(/, price.*$/, "")}
          </span>
        </span>
        <span className="text-right">
          <span className={`num block text-base font-semibold ${tone(item.change_pct)}`}>{pct(item.change_pct)}</span>
          <span className="num block text-[12px] text-muted">{item.summary?.match(/₹[\d,.]+/)?.[0]}</span>
        </span>
      </Link>
      {item.context && (
        <p className="mt-2 pl-[46px] text-xs leading-snug text-muted">
          {item.context_url ? (
            <a href={item.context_url} target="_blank" rel="noopener noreferrer" className="hover:text-accent">
              {item.context} <ArrowUpRight size={11} className="inline" />
            </a>
          ) : (
            item.context
          )}
          {lead && (
            <>
              {" · "}
              <Link href={`/people/${lead.person_id}`} className="font-medium text-accent">
                Ask {lead.name}
              </Link>
            </>
          )}
        </p>
      )}
    </div>
  );
}
