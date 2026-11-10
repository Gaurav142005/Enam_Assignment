"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pencil, Plus } from "lucide-react";
import type { Holding } from "@/lib/types";
import { HoldingForm } from "./HoldingForm";

/** On a company page: add it to the portfolio, or edit / remove the holding. */
export function HoldingControls({ ticker, holding, lastClose }: { ticker: string; holding: Holding | null; lastClose: number | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  if (!open)
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1.5 text-xs font-medium text-accent">
        {holding ? <Pencil size={13} /> : <Plus size={14} />}
        {holding ? "Edit holding" : "Add to portfolio"}
      </button>
    );
  return (
    <div className="card mt-3 p-4">
      <p className="mb-3 text-sm font-semibold">{holding ? `Edit your ${ticker} holding` : `Add ${ticker} to your portfolio`}</p>
      <HoldingForm
        ticker={ticker}
        existing={holding ? { qty: holding.qty, avg_cost: holding.avg_cost, bought: null } : null}
        lastClose={lastClose}
        onCancel={() => setOpen(false)}
        onDone={() => {
          setOpen(false);
          router.refresh();
        }}
      />
    </div>
  );
}
