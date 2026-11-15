import {
  BadgeCheck, Banknote, BarChart3, Coins, Eye, Factory, FileText, GitMerge, Lock, Megaphone, Mic, Scale, Split, UserRound, Users, Vote,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Category } from "@/lib/types";

export const CATEGORY_ICON: Record<Category, LucideIcon> = {
  results: BarChart3, management_change: UserRound, "M&A": GitMerge, litigation: Scale, pledging: Lock, fund_raise: Banknote,
  capex: Factory, credit_rating: BadgeCheck, insider_trading: Eye, press_release: Megaphone, bonus_split: Split, dividend: Coins,
  earnings_call: Mic, investor_meetings: Users, agm_egm: Vote, postal_ballot: Vote, unclassified: FileText,
};
