/** Trend shape for a list row: muted 2px line, hairline at the period's start value, end dot in the direction color. */
export function Sparkline({ values, width = 72, height = 28, label }: { values: number[]; width?: number; height?: number; label: string }) {
  if (values.length < 2) return <span style={{ width, height }} className="inline-block" />;
  const pad = 4;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2);
  const y = (v: number) => pad + (1 - (v - min) / span) * (height - pad * 2);
  const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const first = values[0];
  const last = values[values.length - 1];
  const dir = last > first ? "rgb(var(--up))" : last < first ? "rgb(var(--down))" : "rgb(var(--muted))";
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} className="shrink-0 overflow-visible">
      <line x1={pad} x2={width - pad} y1={y(first)} y2={y(first)} stroke="rgb(var(--line))" strokeWidth={1} />
      <polyline points={pts} fill="none" stroke="rgb(var(--muted))" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" opacity={0.55} />
      <circle cx={x(values.length - 1)} cy={y(last)} r={3.5} fill={dir} stroke="rgb(var(--surface))" strokeWidth={2} />
    </svg>
  );
}
