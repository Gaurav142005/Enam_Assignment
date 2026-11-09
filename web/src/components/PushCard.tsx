import Link from "next/link";
import {
  Activity, ArrowUpRight, BadgeCheck, Banknote, BarChart3, ChevronDown, Coins, Eye, Factory, FileText, GitMerge, Lock,
  Megaphone, Mic, Scale, Split, TrendingDown, TrendingUp, UserRound, Users, Vote,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ago, CATEGORY_LABEL, pct, tone } from "@/lib/format";
import type { Category, PushItem } from "@/lib/types";
import { NetworkLine } from "./NetworkLine";
import { PersonBrief } from "./PersonBrief";
import { ResultsTable } from "./ResultsTable";
import { TickerBadge } from "./TickerBadge";

export const CATEGORY_ICON: Record<Category, LucideIcon> = {
  results: BarChart3, management_change: UserRound, "M&A": GitMerge, litigation: Scale, pledging: Lock, fund_raise: Banknote,
  capex: Factory, credit_rating: BadgeCheck, insider_trading: Eye, press_release: Megaphone, bonus_split: Split, dividend: Coins,
  earnings_call: Mic, investor_meetings: Users, agm_egm: Vote, postal_ballot: Vote, unclassified: FileText,
};

const PRIORITY: Record<PushItem["priority"], { label: string; dot: string } | null> = {
  critical: { label: "Critical", dot: "bg-down" },
  high: { label: "High", dot: "bg-warn" },
  normal: null,
  routine: null,
};

/** One line that says why this card matters, before any detail is opened. */
function KeyLine({ item }: { item: PushItem }) {
  const r = item.results;
  if (r) {
    const rev = r.rows.find((x) => x.metric === "Revenue");
    const pat = r.rows.find((x) => x.metric === "PAT");
    return (
      <p className="text-[13px] text-muted">
        {rev && (
          <>
            Revenue <span className={`num font-semibold ${tone(rev.yoy_pct)}`}>{pct(rev.yoy_pct)}</span>
          </>
        )}
        {pat && (
          <>
            {" · "}PAT <span className={`num font-semibold ${tone(pat.yoy_pct)}`}>{pct(pat.yoy_pct)}</span>
          </>
        )}{" "}
        YoY
      </p>
    );
  }
  if (item.person) return <p className="text-[13px] text-muted">{item.person.bio ?? item.person.headline}</p>;
  if (item.summary) return <p className="text-[13px] text-muted">{item.summary}</p>;
  return null;
}

export function PushCard({ item }: { item: PushItem }) {
  const pr = PRIORITY[item.priority];
  const Icon = item.category ? CATEGORY_ICON[item.category] : FileText;
  const title = item.results ? `${item.results.period} results` : item.title;
  const [lead, ...more] = item.network;
  const hasDetails = !!(item.results || item.person || more.length || item.source_url);

  return (
    <article className="card overflow-hidden">
      <div className="space-y-3 p-4">
        <header className="flex items-center gap-3">
          <TickerBadge ticker={item.ticker} />
          <div className="min-w-0 flex-1">
            <Link href={`/company/${item.ticker}`} className="block truncate text-sm font-semibold">
              {item.ticker} <span className="font-normal text-muted">· {item.company_name}</span>
            </Link>
            <p className="flex items-center gap-1.5 text-xs text-muted">
              <Icon size={13} aria-hidden />
              {item.category ? CATEGORY_LABEL[item.category] : "Update"}
              {pr && (
                <>
                  <span aria-hidden>·</span>
                  <span className={`h-1.5 w-1.5 rounded-full ${pr.dot}`} aria-hidden />
                  {pr.label}
                </>
              )}
            </p>
          </div>
          <span className="num self-start text-xs text-muted">{ago(item.at)}</span>
        </header>

        <div className="space-y-1">
          <h3 className="text-base font-semibold leading-snug">{title}</h3>
          <KeyLine item={item} />
        </div>

        {lead && <NetworkLine hint={lead} lead={item.person ? "Knows them:" : "Ask"} />}
      </div>

      {hasDetails && (
        <details className="group border-t border-line">
          <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-xs font-medium text-muted">
            <span className="group-open:hidden">Details</span>
            <span className="hidden group-open:inline">Hide details</span>
            <ChevronDown size={16} className="transition-transform group-open:rotate-180" />
          </summary>
          <div className="space-y-3 px-4 pb-4">
            {item.results && <ResultsTable r={item.results} />}
            {item.person && <PersonBrief p={item.person} />}
            {more.length > 0 && (
              <div className="space-y-1.5">
                <p className="eyebrow">Also in your network</p>
                {more.map((h) => (
                  <NetworkLine key={h.person_id} hint={h} lead={item.person ? "Knows them:" : "Ask"} />
                ))}
              </div>
            )}
            {(item.results || item.source_url) && (
              <div className="flex items-start justify-between gap-3 text-xs text-muted">
                {item.results && <span className="min-w-0">{item.title}</span>}
                {item.source_url && (
                  <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="ml-auto flex shrink-0 items-center gap-0.5 font-medium text-accent">
                    Filing <ArrowUpRight size={13} />
                  </a>
                )}
              </div>
            )}
          </div>
        </details>
      )}
    </article>
  );
}

/** EOD trigger as a compact tile: the move is the headline. */
export function MoveTile({ item }: { item: PushItem }) {
  const up = (item.change_pct ?? 0) >= 0;
  const vol = item.kind === "volume_spike";
  const Icon = vol ? Activity : up ? TrendingUp : TrendingDown;
  return (
    <Link href={`/company/${item.ticker}`} className="card block p-3.5 active:opacity-70">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{item.ticker}</span>
        <Icon size={16} className={vol ? "text-warn" : up ? "text-up-ink" : "text-down-ink"} aria-label={vol ? "Volume spike" : up ? "Up" : "Down"} />
      </div>
      <p className={`num mt-2 text-xl font-semibold ${tone(item.change_pct)}`}>{pct(item.change_pct)}</p>
      <p className="mt-0.5 text-xs leading-snug text-muted">{vol ? item.title.replace(/, price.*$/, "") : `Closed ${item.summary?.match(/₹[\d,.]+/)?.[0] ?? ""}`}</p>
    </Link>
  );
}
