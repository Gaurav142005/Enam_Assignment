import { ChevronDown } from "lucide-react";
import { BackLink } from "@/components/BackLink";
import { NetworkLine } from "@/components/NetworkLine";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { Empty } from "@/components/States";
import { api } from "@/lib/api";
import type { ResearchReport } from "@/lib/types";

/** PULL — the research view. "Promised vs delivered" leads; every claim will cite a primary source. */
export default async function CompanyPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const r = await api<ResearchReport>(`/pull/research/${encodeURIComponent(ticker)}`);
  const c = r.company;

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title={c.ticker} sub={`${c.name}${c.sector !== "—" ? ` · ${c.sector}` : ""}${c.in_portfolio ? " · In portfolio" : ""}`} />

      <SectionTitle>Who can help</SectionTitle>
      {r.network.length ? (
        <div className="space-y-1.5 px-4">
          {r.network.map((h) => (
            <NetworkLine key={h.person_id} hint={h} />
          ))}
        </div>
      ) : (
        <Empty>No one in your network has worked here yet.</Empty>
      )}

      <SectionTitle>Research</SectionTitle>
      <div className="card mx-4 divide-y divide-line">
        {r.sections.map((s, idx) => (
          <details key={s.key} open={idx === 0} className="group">
            <summary className="flex cursor-pointer items-center justify-between px-4 py-3.5">
              <span className="text-[15px] font-medium">{s.title}</span>
              <span className="flex items-center gap-2 text-xs text-muted">
                {s.status === "pending" && "Not built yet"}
                <ChevronDown size={16} className="transition-transform group-open:rotate-180" />
              </span>
            </summary>
            <div className="px-4 pb-4 text-sm text-muted">
              {s.body ?? "Will be generated from annual reports and concall transcripts, with page citations."}
            </div>
          </details>
        ))}
      </div>
    </main>
  );
}
