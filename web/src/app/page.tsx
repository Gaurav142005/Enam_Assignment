import Link from "next/link";
import { Suspense } from "react";
import { SlidersHorizontal } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { MoveRow, PushCard } from "@/components/PushCard";
import { DemoNote, Empty } from "@/components/States";
import { WindowPicker } from "@/components/WindowPicker";
import { api } from "@/lib/api";
import { ago, CATEGORY_LABEL, windowLabel } from "@/lib/format";
import type { Digest } from "@/lib/types";

/** PUSH — the Brief. What changed across my portfolio, ranked; routine collapsed; network woven in. */
export default async function BriefPage({ searchParams }: { searchParams: Promise<{ h?: string }> }) {
  const hours = Number((await searchParams).h) || 24;
  const d = await api<Digest>(`/push/digest?hours=${hours}`);
  const routineCount = d.routine.reduce((n, g) => n + g.count, 0);

  return (
    <main>
      <PageHeader
        title="Brief"
        sub={`${d.attention.length} need you · ${d.moves.length} unusual moves · ${routineCount} routine`}
        right={
          <Link href="/settings" aria-label="Alert settings" className="mb-1 rounded-full p-2 text-muted active:bg-line/50">
            <SlidersHorizontal size={20} />
          </Link>
        }
      />
      <div className="px-4">
        <Suspense>
          <WindowPicker value={hours} />
        </Suspense>
      </div>

      <SectionTitle>Needs your attention</SectionTitle>
      {d.attention.length ? (
        <div className="space-y-3 px-4">
          {d.attention.map((i) => (
            <PushCard key={i.id} item={i} />
          ))}
        </div>
      ) : (
        <Empty>Nothing material in the last {windowLabel(hours)}.</Empty>
      )}

      {d.moves.length > 0 && (
        <>
          <SectionTitle right={<Link href="/settings" className="text-xs text-accent">Thresholds</Link>}>
            Unusual moves
          </SectionTitle>
          <div className="card mx-4 divide-y divide-line">
            {d.moves.map((m) => (
              <MoveRow key={m.id} item={m} />
            ))}
          </div>
        </>
      )}

      {d.routine.length > 0 && (
        <>
          <SectionTitle>Routine</SectionTitle>
          <div className="card mx-4 divide-y divide-line">
            {d.routine.map((g) => (
              <details key={g.category} className="group">
                <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm">
                  <span>{CATEGORY_LABEL[g.category]}</span>
                  <span className="num text-muted group-open:text-ink">{g.count}</span>
                </summary>
                <ul className="space-y-2 px-4 pb-3">
                  {g.items.map((i) => (
                    <li key={i.id} className="flex gap-2 text-[13px]">
                      <span className="w-20 shrink-0 font-medium">{i.ticker}</span>
                      <span className="flex-1 text-muted">{i.title}</span>
                      <span className="num text-xs text-muted">{ago(i.at)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </>
      )}
      <DemoNote />
    </main>
  );
}
