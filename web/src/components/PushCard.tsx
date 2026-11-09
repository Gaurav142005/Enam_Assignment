import Link from "next/link";
import { ago, CATEGORY_LABEL } from "@/lib/format";
import type { PushItem } from "@/lib/types";
import { NetworkLine } from "./NetworkLine";
import { PersonBrief } from "./PersonBrief";
import { ResultsTable } from "./ResultsTable";

const RAIL: Record<PushItem["priority"], string> = {
  critical: "bg-down",
  high: "bg-warn",
  normal: "bg-line",
  routine: "bg-transparent",
};

export function PushCard({ item }: { item: PushItem }) {
  return (
    <article className="card relative overflow-hidden">
      <span className={`absolute inset-y-0 left-0 w-1 ${RAIL[item.priority]}`} aria-hidden />
      <div className="space-y-3 p-4 pl-5">
        <header className="flex items-center gap-2 text-xs text-muted">
          <Link href={`/company/${item.ticker}`} className="font-semibold text-ink">
            {item.ticker}
          </Link>
          {item.category && <span>· {CATEGORY_LABEL[item.category]}</span>}
          <span className="ml-auto num">{ago(item.at)}</span>
        </header>

        <div>
          <h3 className="text-[15px] font-medium leading-snug">{item.title}</h3>
          {item.summary && <p className="mt-1 text-[13px] text-muted">{item.summary}</p>}
        </div>

        {item.results && <ResultsTable r={item.results} />}
        {item.person && <PersonBrief p={item.person} />}

        {item.network.length > 0 && (
          <div className="space-y-1.5">
            {item.network.map((h) => (
              <NetworkLine key={h.person_id} hint={h} lead={item.person ? "Knows them:" : "Ask"} />
            ))}
          </div>
        )}
      </div>
    </article>
  );
}

export function MoveRow({ item }: { item: PushItem }) {
  const down = (item.change_pct ?? 0) < 0;
  return (
    <Link href={`/company/${item.ticker}`} className="flex items-center gap-3 px-4 py-3 active:bg-line/40">
      <span className={`h-2 w-2 shrink-0 rounded-full ${item.kind === "volume_spike" ? "bg-warn" : down ? "bg-down" : "bg-up"}`} />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium">
          {item.ticker} <span className="font-normal text-muted">· {item.title}</span>
        </span>
        {item.summary && <span className="num block text-xs text-muted">{item.summary}</span>}
      </span>
    </Link>
  );
}
