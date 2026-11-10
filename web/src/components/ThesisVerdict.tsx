import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { ThesisCheck } from "@/lib/types";

/** "Supports / challenges your thesis" with the fact that decided it. Icon + words, never colour alone. */
export function ThesisVerdict({ check, compact = false }: { check: ThesisCheck; compact?: boolean }) {
  const supports = check.stance === "supports";
  const Icon = supports ? ShieldCheck : ShieldAlert;
  return (
    <p className={`flex gap-1.5 text-[13px] leading-snug ${compact ? "" : "rounded-xl px-3 py-2"} ${!compact && (supports ? "bg-up/10" : "bg-down/10")}`}>
      <Icon size={15} className={`mt-px shrink-0 ${supports ? "text-up-ink" : "text-down-ink"}`} aria-hidden />
      <span>
        <span className={`font-medium ${supports ? "text-up-ink" : "text-down-ink"}`}>{supports ? "Supports your thesis" : "Challenges your thesis"}</span>
        {check.why && <span className="text-muted">: {check.why}</span>}
      </span>
    </p>
  );
}
