"use client";

import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { compact, pct, rupees, shortDate, tone } from "@/lib/format";
import type { Bar, PriceHistory, PriceRange } from "@/lib/types";
import { Segmented } from "./Segmented";

const RANGES: PriceRange[] = ["1M", "3M", "6M", "1Y", "5Y"];
type Mode = "Candles" | "Line";

/** Read a design token ("11 138 122") as an rgba() string the chart library understands. */
function token(name: string, alpha = 1): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim().split(/\s+/).join(", ");
  return `rgba(${v}, ${alpha})`;
}

function themeOptions() {
  return {
    layout: {
      background: { type: ColorType.Solid, color: "transparent" },
      textColor: token("muted"),
      fontFamily: getComputedStyle(document.body).fontFamily,
      fontSize: 11,
      attributionLogo: false,
      panes: { separatorColor: token("line"), separatorHoverColor: token("line") },
    },
    grid: { vertLines: { visible: false }, horzLines: { color: token("line"), style: LineStyle.Solid } },
    crosshair: {
      mode: CrosshairMode.Magnet, // snaps to the session; readers aim at a date, not a wick
      vertLine: { color: token("muted", 0.6), width: 1 as const, style: LineStyle.Solid, labelBackgroundColor: token("ink") },
      horzLine: { color: token("muted", 0.4), width: 1 as const, style: LineStyle.Solid, labelBackgroundColor: token("ink") },
    },
  };
}

function seriesColors() {
  return {
    candle: {
      // Direction is double-encoded: hue AND fill (hollow = up, solid = down), so it survives colour-blindness and print.
      upColor: token("surface"),
      borderUpColor: token("up"),
      wickUpColor: token("up"),
      downColor: token("down"),
      borderDownColor: token("down"),
      wickDownColor: token("down"),
    },
    area: { lineColor: token("accent"), topColor: token("accent", 0.12), bottomColor: token("accent", 0) },
    volUp: token("up", 0.45),
    volDown: token("down", 0.45),
  };
}

export function PriceChart({ ticker }: { ticker: string }) {
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candles = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const area = useRef<ISeriesApi<"Area"> | null>(null);
  const volume = useRef<ISeriesApi<"Histogram"> | null>(null);

  const [range, setRange] = useState<PriceRange>("6M");
  const [mode, setMode] = useState<Mode>("Candles");
  const [bars, setBars] = useState<Bar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<number | null>(null); // index into bars

  // Build the chart once.
  useEffect(() => {
    if (!box.current) return;
    const c = createChart(box.current, {
      autoSize: true,
      ...themeOptions(),
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.08, bottom: 0.04 } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true, lockVisibleTimeRangeOnResize: true },
      handleScroll: false, // the range filter sets the window; touches on the chart drive the crosshair, not a pan
      handleScale: false,
    });
    // Rupee formatting on the price series only; the volume pane keeps its own compact volume scale.
    const priceFormat = { type: "custom" as const, minMove: 0.05, formatter: (p: number) => `₹${p.toLocaleString("en-IN", { maximumFractionDigits: p < 100 ? 2 : 0 })}` };
    const colors = seriesColors();
    candles.current = c.addSeries(CandlestickSeries, { ...colors.candle, priceFormat, priceLineVisible: false, lastValueVisible: true });
    area.current = c.addSeries(AreaSeries, { ...colors.area, priceFormat, lineWidth: 2, priceLineVisible: false, visible: false });
    volume.current = c.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false }, 1);
    c.panes()[0]?.setStretchFactor(3);
    c.panes()[1]?.setStretchFactor(1);
    chart.current = c;

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const retheme = () => {
      const col = seriesColors();
      c.applyOptions(themeOptions());
      candles.current?.applyOptions(col.candle);
      area.current?.applyOptions(col.area);
      setBars((b) => [...b]); // re-tint volume bars
    };
    media.addEventListener("change", retheme);
    return () => {
      media.removeEventListener("change", retheme);
      c.remove();
      chart.current = null;
    };
  }, []);

  // Fetch on ticker/range change. Keep the previous render (dimmed) while loading — no layout jump.
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    api<PriceHistory>(`/market/prices/${encodeURIComponent(ticker)}?range=${range}`)
      .then((h) => live && setBars(h.bars))
      .catch((e: Error) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [ticker, range]);

  // Push data into the series.
  useEffect(() => {
    if (!chart.current || !candles.current || !area.current || !volume.current) return;
    const col = seriesColors();
    candles.current.setData(bars.map((b) => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })));
    area.current.setData(bars.map((b) => ({ time: b.time as Time, value: b.close })));
    volume.current.setData(
      bars.map((b, i) => ({
        time: b.time as Time,
        value: b.volume,
        color: b.close >= (i ? bars[i - 1].close : b.open) ? col.volUp : col.volDown,
      })),
    );
    chart.current.timeScale().fitContent();
  }, [bars]);

  useEffect(() => {
    candles.current?.applyOptions({ visible: mode === "Candles" });
    area.current?.applyOptions({ visible: mode === "Line" });
  }, [mode]);

  // Crosshair → readout.
  const index = useMemo(() => new Map(bars.map((b, i) => [b.time, i])), [bars]);
  useEffect(() => {
    const c = chart.current;
    if (!c) return;
    const onMove = (p: MouseEventParams<Time>) => setHover(p.time ? (index.get(p.time as string) ?? null) : null);
    c.subscribeCrosshairMove(onMove);
    return () => c.unsubscribeCrosshairMove(onMove);
  }, [index]);

  const i = hover ?? bars.length - 1;
  const bar = bars[i];
  const prev = i > 0 ? bars[i - 1] : null;
  const dayChg = bar && prev ? (bar.close / prev.close - 1) * 100 : null;
  const rangeChg = bars.length > 1 ? (bars[bars.length - 1].close / bars[0].close - 1) * 100 : null;

  return (
    <section className="card mx-4 overflow-hidden" aria-label={`${ticker} price chart`}>
      <div className="flex items-start justify-between gap-3 px-4 pt-4">
        <div className="min-w-0">
          <p className="text-2xl font-semibold tracking-tight">{bar ? rupees(bar.close) : "—"}</p>
          <p className="mt-0.5 text-xs text-muted">
            {bar ? (
              <>
                <span className={`num font-medium ${tone(dayChg)}`}>{pct(dayChg)}</span> on {shortDate(bar.time)}
                {hover === null && rangeChg !== null && (
                  <>
                    {" · "}
                    <span className={`num font-medium ${tone(rangeChg)}`}>{pct(rangeChg)}</span> over {range}
                  </>
                )}
              </>
            ) : (
              "Loading…"
            )}
          </p>
        </div>
        <Segmented value={mode} options={["Candles", "Line"]} label="Chart type" onChange={(m) => setMode(m as Mode)} />
      </div>

      {/* OHLC readout: values lead, labels follow. */}
      <dl className="num mt-3 grid grid-cols-5 gap-1 px-4 text-[11px]">
        {(
          [
            ["Open", bar && rupees(bar.open, 0)],
            ["High", bar && rupees(bar.high, 0)],
            ["Low", bar && rupees(bar.low, 0)],
            ["Close", bar && rupees(bar.close, 0)],
            ["Vol", bar && compact(bar.volume)],
          ] as const
        ).map(([k, v]) => (
          <div key={k} className="min-w-0">
            <dd className="truncate font-medium text-ink">{v ?? "—"}</dd>
            <dt className="text-muted">{k}</dt>
          </div>
        ))}
      </dl>

      <div className={`relative mt-2 h-80 transition-opacity ${loading && bars.length ? "opacity-50" : ""}`}>
        <div ref={box} className="absolute inset-0" />
        {!loading && !bars.length && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-muted">{error ?? "No price history for this ticker."}</p>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-line px-4 py-2.5">
        <Segmented value={range} options={RANGES} label="Chart range" onChange={(r) => setRange(r as PriceRange)} />
        <span className="text-[11px] text-muted">Daily · NSE</span>
      </div>
    </section>
  );
}
