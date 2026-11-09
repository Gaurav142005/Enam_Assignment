import { crore, pct } from "@/lib/format";
import type { ResultsCut } from "@/lib/types";

function Delta({ v }: { v: number | null }) {
  const tone = v === null ? "text-muted" : v >= 0 ? "text-up-ink" : "text-down-ink";
  return <td className={`num py-1.5 text-right ${tone}`}>{pct(v)}</td>;
}

export function ResultsTable({ r }: { r: ResultsCut }) {
  return (
    <table className="w-full text-[13px]">
      <thead>
        <tr className="text-muted">
          <th className="pb-1 text-left font-normal">{r.period}</th>
          <th className="pb-1 text-right font-normal">{r.unit}</th>
          <th className="pb-1 text-right font-normal">QoQ</th>
          <th className="pb-1 text-right font-normal">YoY</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-line">
        {r.rows.map((row) => (
          <tr key={row.metric}>
            <td className="py-1.5">{row.metric}</td>
            <td className="num py-1.5 text-right">{crore(row.value)}</td>
            <Delta v={row.qoq_pct} />
            <Delta v={row.yoy_pct} />
          </tr>
        ))}
      </tbody>
    </table>
  );
}
