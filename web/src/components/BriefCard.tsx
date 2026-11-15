"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { ago, CATEGORY_LABEL, pct, tenure, tone } from "@/lib/format";
import type { PushItem } from "@/lib/types";
import { CATEGORY_ICON } from "./categoryIcons";
import { NetworkLine } from "./NetworkLine";
import { ResultsTable } from "./ResultsTable";
import { ThesisVerdict } from "./ThesisVerdict";
import { TickerBadge } from "./TickerBadge";

const PRIORITY: Record<PushItem["priority"], { label: string; dot: string } | null> = {
  critical: { label: "Critical", dot: "bg-down" },
  high: { label: "High", dot: "bg-warn" },
  normal: null,
  routine: null,
};

function ResultsLine({ item }: { item: PushItem }) {
  const r = item.results!;
  const rev = r.rows.find((x) => x.metric === "Revenue");
  const pat = r.rows.find((x) => x.metric === "PAT");
  return (
    <p className="text-[14px] text-muted">
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

/**
 * A Brief card. Closed: the headline, one line of substance, the best person to ask. Opened: the whole story in the
 * card itself (full text, numbers, the person's background), then only the contacts and the source below.
 */
export function BriefCard({ item }: { item: PushItem }) {
  const [open, setOpen] = useState(false);
  const pr = PRIORITY[item.priority];
  const Icon = item.category ? CATEGORY_ICON[item.category] : CATEGORY_ICON.unclassified;
  const title = item.results ? `${item.results.period} results` : item.title;
  const p = item.person;
  const text = p ? p.bio ?? p.headline : item.summary;
  const [lead, ...more] = item.network;
  const clamp = open ? "" : "line-clamp-3";
  const canOpen = !!(item.results || (text && text.length > 160) || title.length > 110 || p?.positions.length || p?.education.length || more.length || item.source_url);

  return (
    <article className="card flex h-full flex-col overflow-hidden">
      <div className="flex-1 space-y-3 p-4">
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
          <span className="flex items-center gap-1.5 self-start">
            {item.is_new && <span className="rounded-full bg-accent px-1.5 py-px text-[11px] font-semibold text-bg">New</span>}
            <span className="num text-xs text-muted">{ago(item.at)}</span>
          </span>
        </header>

        <div className="space-y-1.5">
          <h3 className={`text-base font-semibold leading-snug ${clamp}`}>{title}</h3>
          {item.results && <ResultsLine item={item} />}
          {text && <p className={`text-[14px] leading-relaxed text-muted ${clamp}`}>{text}</p>}
        </div>

        {/* The extra detail slides open in place (grid 0fr → 1fr animates to the content's real height). */}
        <div className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-out motion-reduce:transition-none ${open ? "grid-rows-[1fr] opacity-100" : "!mt-0 grid-rows-[0fr] opacity-0"}`} inert={!open}>
          <div className="min-h-0 space-y-3 overflow-hidden">

            {item.results && <ResultsTable r={item.results} />}
            {p && (p.positions.length > 1 || p.education.length > 0) && (
              <div className="space-y-0.5 text-[14px] leading-snug">
                {p.positions.slice(1, 4).map((pos) => (
                  <p key={`${pos.company}-${pos.title}`} className="text-muted">
                    <span className="text-ink/80">Before:</span> {[pos.title, pos.company].filter(Boolean).join(", ")}
                    {pos.start !== null && ` · ${tenure(pos.start, pos.end)}`}
                  </p>
                ))}
                {p.education.slice(0, 2).map((e) => (
                  <p key={e.school} className="text-muted">
                    <span className="text-ink/80">Studied:</span> {[e.degree, e.school].filter(Boolean).join(", ")}
                  </p>
                ))}
                <Link href={`/people/${p.id}`} className="inline-block pt-1 text-[13px] font-medium text-accent">
                  Full profile and who can reach {p.name.split(" ")[0]}
                </Link>
              </div>
            )}
            {item.results && item.title && <p className="text-xs text-muted">{item.title}</p>}
          </div>
        </div>

        {item.thesis && <ThesisVerdict check={item.thesis} />}

        {lead && <NetworkLine hint={lead} lead={lead.relation === "overlap" ? "Reach via" : "Ask"} />}
        {(more.length > 0 || item.source_url) && (
          <div className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ease-out motion-reduce:transition-none ${open ? "grid-rows-[1fr] opacity-100" : "!mt-0 grid-rows-[0fr] opacity-0"}`} inert={!open}>
            <div className="min-h-0 space-y-3 overflow-hidden">
              {more.map((h) => <NetworkLine key={h.person_id} hint={h} lead={h.relation === "overlap" ? "Reach via" : "Ask"} />)}
              {item.source_url && (
                <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-xs font-medium text-accent">
                  Open the filing <ArrowUpRight size={13} />
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {canOpen && (
        <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex items-center justify-between border-t border-line px-4 py-2.5 text-xs font-medium text-muted">
          {open ? "Show less" : "Read more"}
          <ChevronDown size={16} className={`transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
        </button>
      )}
    </article>
  );
}
