"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Check, MessageCircle } from "lucide-react";
import { apiPost } from "@/lib/api";

/** One tap after a call: keeps "last spoke" honest, which is what the reconnect nudges run on. */
export function LogContact({ id }: { id: string }) {
  const router = useRouter();
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={async () => {
        await apiPost(`/network/people/${id}/contact`, {});
        setDone(true);
        router.refresh();
      }}
      disabled={done}
      className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3.5 py-2 text-[13px] font-medium disabled:text-up-ink"
    >
      {done ? <Check size={15} /> : <MessageCircle size={15} />}
      {done ? "Logged for today" : "We spoke today"}
    </button>
  );
}
