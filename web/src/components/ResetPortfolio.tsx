"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, apiPost } from "@/lib/api";

/** Public demo only: visitors edit a shared portfolio, so offer a way back to the original. */
export function ResetPortfolio() {
  const router = useRouter();
  const [show, setShow] = useState(false);
  useEffect(() => {
    api<{ public_demo: boolean }>("/network/config").then((c) => setShow(c.public_demo)).catch(() => {});
  }, []);
  if (!show) return null;
  return (
    <button
      onClick={async () => {
        if (!confirm("Restore the demo portfolio? Holdings added or removed here will be undone.")) return;
        await apiPost("/portfolio/holdings/reset", {});
        router.refresh();
      }}
      className="mx-auto mt-3 block text-xs font-medium text-accent"
    >
      Reset to the demo portfolio
    </button>
  );
}
