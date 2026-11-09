"use client";

import { ChevronLeft } from "lucide-react";
import { useRouter } from "next/navigation";

export function BackLink() {
  const router = useRouter();
  return (
    <button
      onClick={() => (history.length > 1 ? router.back() : router.push("/"))}
      className="-ml-2 flex items-center px-2 pt-[calc(env(safe-area-inset-top)+0.75rem)] text-sm text-accent"
    >
      <ChevronLeft size={18} /> Back
    </button>
  );
}
