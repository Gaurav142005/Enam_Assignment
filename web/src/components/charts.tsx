"use client";

import { useState } from "react";
import { periodLabel, unitValue } from "@/lib/format";
import type { Series } from "@/lib/types";

// Categorical slots in fixed order (never cycled); identity also carried by the legend + readout text.
const SLOT = ["rgb(var(--series-1))", "rgb(var(--series-2))", "rgb(var(--series-3))"];
const W = 340;
const PAD = { l: 4, r: 44, t: 8, b: 20 };

function niceTicks(min: number, max: number, n = 3): number[] {
  const span = max - min || Math.abs(max) || 1;
  const raw = span / n;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) ?? raw;
  const lo = Math.floor(min / step) * step;
  const out: number[] = [];
  for (let v = lo; v <= max + step * 0.001; v += step) out.push(+v.toFixed(6));
  if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
  return out;
}

function tickLabel(v: number, unit: string): string {
  if (unit === "%") return `${v}%`;
  if (unit === "x") return `${v}x`;
  if (unit === "days") return `${v}d`;
  const a = Math.abs(v);
  return a >= 1e5 ? `${(v / 1e5).toFixed(a >= 1e6 ? 0 : 1)}L` : a >= 1e3 ? `${(v / 1e3).toFixed(a >= 1e4 ? 0 : 1)}K` : `${v}`;
}

/** Readout above a chart: values lead (strong), series names follow; defaults to the latest period. */
function Readout({ series, i, annual }: { series: Series[]; i: number; annual: boolean }) {
  const period = series[0]?.points[i]?.period ?? "";
  return (
    <div className="mb-1 flex min-h-[2.25rem] flex-wrap items-end gap-x-4 gap-y-0.5 text-xs">
      <span className="w-full text-[11px] text-muted">{periodLabel(period, annual)}</span>
      {series.map((s, k) => (
        <span key={s.key} className="flex items-center gap-1.5">
          {series.length > 1 && <span className="h-0.5 w-3 rounded-full" style={{ background: SLOT[k] }} aria-hidden />}
          <span className="num font-semibold text-ink">{unitValue(s.points[i]?.value ?? null, s.unit)}</span>
          <span className="text-muted">{s.name}</span>
        </span>
      ))}
    </div>
  );
}

function Legend({ series, mark }: { series: Series[]; mark: "rect" | "line" }) {
  if (series.length < 2) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-x-4 text-[11px] text-muted">
      {series.map((s, k) => (
        <span key={s.key} className="flex items-center gap-1.5">
          <span className={mark === "rect" ? "h-2 w-2 rounded-sm" : "h-0.5 w-3 rounded-full"} style={{ background: SLOT[k] }} aria-hidden />
          {s.name}
        </span>
      ))}
    </div>
  );
}

function scaleFor(series: Series[], height: number, zeroBased: boolean) {
  const vals = series.flatMap((s) => s.points.map((p) => p.value)).filter((v): v is number => v !== null);
  const lo = Math.min(zeroBased ? 0 : Infinity, ...vals);
  const hi = Math.max(zeroBased ? 0 : -Infinity, ...vals);
  const pad = zeroBased ? 0 : (hi - lo) * 0.1 || 1;
  const ticks = niceTicks(lo - pad, hi + pad);
  const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
  const y = (v: number) => PAD.t + (1 - (v - y0) / (y1 - y0 || 1)) * (height - PAD.t - PAD.b);
  return { ticks, y };
}

function Axes({ ticks, y, unit, labels, x, annual }: { ticks: number[]; y: (v: number) => number; unit: string; labels: string[]; x: (i: number) => number; annual: boolean }) {
  const every = Math.ceil(labels.length / 6);
  return (
    <>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="rgb(var(--line))" strokeWidth={1} />
          <text x={W - PAD.r + 6} y={y(t) + 3.5} fontSize={10} fill="rgb(var(--muted))" className="num">
            {tickLabel(t, unit)}
          </text>
        </g>
      ))}
      {labels.map((p, i) =>
        (labels.length - 1 - i) % every === 0 ? (
          <text key={p} x={x(i)} y={y(ticks[0]) + 14} fontSize={10} textAnchor="middle" fill="rgb(var(--muted))">
            {periodLabel(p, annual)}
          </text>
        ) : null,
      )}
    </>
  );
}

/** Columns (1–2 series, one unit, one axis). Grouped bars with a 2px gap; 4px rounded data-end, square at the baseline. */
export function ColumnChart({ series, height = 150, annual = true, label }: { series: Series[]; height?: number; annual?: boolean; label: string }) {
  const n = series[0]?.points.length ?? 0;
  const [hover, setHover] = useState<number | null>(null);
  if (!n) return null;
  const i = hover ?? n - 1;
  const { ticks, y } = scaleFor(series, height, true);
  const slot = (W - PAD.l - PAD.r) / n;
  const x = (k: number) => PAD.l + slot * (k + 0.5);
  const bw = Math.min(14, (slot - 6) / series.length - 2);
  const base = y(0);

  const bar = (cx: number, v: number) => {
    const top = y(v);
    const h = Math.abs(base - top);
    const r = Math.min(4, h, bw / 2);
    const x0 = cx - bw / 2;
    return v >= 0
      ? `M${x0},${base} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top + r} V${base} Z`
      : `M${x0},${base} V${top - r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top - r} V${base} Z`;
  };

  return (
    <figure>
      <Readout series={series} i={i} annual={annual} />
      <svg viewBox={`0 0 ${W} ${height}`} className="w-full touch-pan-y" role="img" aria-label={label} onPointerLeave={() => setHover(null)}>
        <Axes ticks={ticks} y={y} unit={series[0].unit} labels={series[0].points.map((p) => p.period)} x={x} annual={annual} />
        {series[0].points.map((_, k) => (
          <g key={k} opacity={hover === null || hover === k ? 1 : 0.45}>
            {series.map((s, si) => {
              const v = s.points[k]?.value;
              if (v === null || v === undefined || v === 0) return null;
              const off = (si - (series.length - 1) / 2) * (bw + 2);
              return <path key={s.key} d={bar(x(k) + off, v)} fill={SLOT[si]} />;
            })}
            {/* hit target: the whole slot, not just the painted bar */}
            <rect x={x(k) - slot / 2} y={0} width={slot} height={height} fill="transparent" onPointerEnter={() => setHover(k)} onPointerDown={() => setHover(k)} />
          </g>
        ))}
        {ticks[0] < 0 && <line x1={PAD.l} x2={W - PAD.r} y1={base} y2={base} stroke="rgb(var(--muted))" strokeWidth={1} />}
      </svg>
      <Legend series={series} mark="rect" />
    </figure>
  );
}

/** Lines (1–3 series, one unit). 2px lines, crosshair snaps to the nearest period, markers ringed in the surface colour. */
export function LineChart({ series, height = 130, annual = true, label }: { series: Series[]; height?: number; annual?: boolean; label: string }) {
  const n = series[0]?.points.length ?? 0;
  const [hover, setHover] = useState<number | null>(null);
  if (n < 2) return null;
  const i = hover ?? n - 1;
  const { ticks, y } = scaleFor(series, height, false);
  const x = (k: number) => PAD.l + 6 + (k / (n - 1)) * (W - PAD.l - PAD.r - 12);

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const k = Math.round(((px - PAD.l - 6) / (W - PAD.l - PAD.r - 12)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, k)));
  };

  return (
    <figure>
      <Readout series={series} i={i} annual={annual} />
      <svg viewBox={`0 0 ${W} ${height}`} className="w-full touch-pan-y" role="img" aria-label={label} onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)}>
        <Axes ticks={ticks} y={y} unit={series[0].unit} labels={series[0].points.map((p) => p.period)} x={x} annual={annual} />
        {hover !== null && <line x1={x(i)} x2={x(i)} y1={PAD.t} y2={height - PAD.b} stroke="rgb(var(--muted))" strokeWidth={1} opacity={0.6} />}
        {series.map((s, si) => {
          const pts = s.points.map((p, k) => (p.value === null ? null : `${x(k).toFixed(1)},${y(p.value).toFixed(1)}`)).filter(Boolean).join(" ");
          const v = s.points[i]?.value;
          return (
            <g key={s.key}>
              <polyline points={pts} fill="none" stroke={SLOT[si]} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {v !== null && v !== undefined && <circle cx={x(i)} cy={y(v)} r={4} fill={SLOT[si]} stroke="rgb(var(--surface))" strokeWidth={2} />}
            </g>
          );
        })}
      </svg>
      <Legend series={series} mark="line" />
    </figure>
  );
}
