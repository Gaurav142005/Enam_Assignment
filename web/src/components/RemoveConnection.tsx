"use client";

import { useRouter } from "next/navigation";
import { apiDelete } from "@/lib/api";

export function RemoveConnection({ id, name }: { id: string; name: string }) {
  const router = useRouter();
  return (
    <button
      onClick={async () => {
        if (!confirm(`Remove ${name} from your network?`)) return;
        await apiDelete(`/network/people/${id}`);
        router.push("/network");
        router.refresh();
      }}
      className="text-xs font-medium text-down-ink"
    >
      Remove from network
    </button>
  );
}
