"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FileUp, ShieldCheck, Users } from "lucide-react";
import { BackLink } from "@/components/BackLink";
import { PageHeader, SectionTitle } from "@/components/PageHeader";
import { api, apiDelete, apiPost, apiUpload } from "@/lib/api";
import type { ImportResult } from "@/lib/types";

/** Import the investor's own LinkedIn connections (their data export), re-upload any time to sync. */
export default function ImportPage() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [removed, setRemoved] = useState<number | null>(null);
  const [publicDemo, setPublicDemo] = useState(false);

  useEffect(() => {
    api<{ public_demo: boolean }>("/network/config").then((c) => setPublicDemo(c.public_demo)).catch(() => {});
  }, []);

  const sample = async () => {
    setBusy(true);
    setError(null);
    setRemoved(null);
    try {
      setResult(await apiPost<ImportResult>("/network/import/sample", {}));
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setRemoved(null);
    try {
      setResult(await apiUpload<ImportResult>("/network/import/linkedin", file));
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm("Remove all connections imported from LinkedIn? Connections you added by hand stay.")) return;
    const r = (await apiDelete("/network/import/linkedin")) as { removed: number };
    setRemoved(r.removed);
    setResult(null);
    router.refresh();
  };

  return (
    <main>
      <div className="px-4">
        <BackLink />
      </div>
      <PageHeader compact title="Import connections" sub="From your LinkedIn data export" />

      {publicDemo && (
        <p className="mx-4 mb-3 rounded-xl border border-warn/40 bg-warn/10 px-3 py-2.5 text-[13px] leading-snug">
          This is a public demo, so uploading your own export is off: anything imported here would be visible to every visitor. Try it with the sample
          instead (15 made-up people at real companies).
        </p>
      )}
      <div className="mx-4 mb-3">
        <button onClick={sample} disabled={busy} className="flex w-full items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-4 text-left active:opacity-70 disabled:opacity-50">
          <Users size={22} className="shrink-0 text-accent" />
          <span className="min-w-0">
            <span className="block text-sm font-medium">Try with sample connections</span>
            <span className="block text-xs text-muted">See how an export maps onto your companies, with no data of your own</span>
          </span>
        </button>
      </div>
      {!publicDemo && (
        <>
      <ol className="card mx-4 space-y-2 p-4 text-[13px] leading-snug">
        <li>
          <span className="font-medium">1.</span> On LinkedIn: <span className="text-muted">Settings → Data privacy → Get a copy of your data</span>
        </li>
        <li>
          <span className="font-medium">2.</span> Choose <span className="text-muted">Connections</span> (usually ready in about 10 minutes, sent by email)
        </li>
        <li>
          <span className="font-medium">3.</span> Upload the <span className="font-mono text-[12px]">Connections.csv</span> or the whole <span className="font-mono text-[12px]">.zip</span> here
        </li>
      </ol>

      <div className="mx-4 mt-3">
        <input
          ref={input}
          type="file"
          accept=".csv,.zip,text/csv,application/zip"
          className="sr-only"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setResult(null);
            setError(null);
          }}
        />
        <button
          onClick={() => input.current?.click()}
          className="flex w-full items-center gap-3 rounded-2xl border border-dashed border-line bg-surface px-4 py-5 text-left active:opacity-70"
        >
          <FileUp size={22} className="shrink-0 text-accent" />
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{file ? file.name : "Choose Connections.csv or export .zip"}</span>
            <span className="block text-xs text-muted">{file ? `${(file.size / 1024).toFixed(0)} KB` : "Re-upload any time: FINN syncs to the latest file"}</span>
          </span>
        </button>
        <button
          onClick={upload}
          disabled={!file || busy}
          className="mt-3 w-full rounded-full bg-ink py-3 text-sm font-medium text-bg disabled:opacity-40"
        >
          {busy ? "Importing…" : "Import"}
        </button>
      </div>
        </>
      )}
      <div className="mx-4">
        {error && <p className="mt-3 text-sm text-down-ink">{error}</p>}
        {removed !== null && <p className="mt-3 text-sm text-muted">Removed {removed} imported connections.</p>}
      </div>

      {result && (
        <>
          <SectionTitle>Imported</SectionTitle>
          <div className="card mx-4 grid grid-cols-3 gap-2 p-4 text-center">
            {[
              ["Connections", result.total],
              ["New", result.added],
              ["At your companies", result.at_portfolio],
            ].map(([k, v]) => (
              <div key={k}>
                <p className="text-xl font-semibold">{v}</p>
                <p className="text-[11px] text-muted">{k}</p>
              </div>
            ))}
          </div>
          {result.removed > 0 && <p className="mx-4 mt-2 text-xs text-muted">{result.removed} no longer in your export were removed.</p>}
          {result.linked.length > 0 && (
            <>
              <SectionTitle>Listed companies they work at</SectionTitle>
              <ul className="card mx-4 divide-y divide-line">
                {result.linked.map((l) => (
                  <li key={l.ticker}>
                    <Link href={`/company/${l.ticker}`} className="flex items-center justify-between px-4 py-3 text-sm active:bg-line/40">
                      <span>
                        <span className="font-medium">{l.ticker}</span>
                        {l.in_portfolio && <span className="ml-2 rounded-full bg-accent-soft px-2 py-0.5 text-[10px] text-accent">portfolio</span>}
                        <span className="block text-xs text-muted">{l.name}</span>
                      </span>
                      <span className="num text-muted">{l.count}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
          <div className="mx-4 mt-4">
            <Link href="/network" className="block w-full rounded-full border border-line py-3 text-center text-sm font-medium">
              See your network
            </Link>
          </div>
        </>
      )}

      <div className="mx-4 mt-6 flex gap-3 rounded-2xl bg-accent-soft/50 p-4 text-xs leading-relaxed text-muted">
        <ShieldCheck size={18} className="mt-0.5 shrink-0 text-accent" />
        <p>
          Stored only in this FINN deployment. Email addresses in the export are dropped on read, and nothing is sent to an AI model.
          FINN never logs into or scrapes LinkedIn.{" "}
          <button onClick={remove} className="font-medium text-down-ink underline-offset-2 hover:underline">
            Remove imported connections
          </button>
        </p>
      </div>
    </main>
  );
}
