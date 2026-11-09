// Mirror of api/app/models.py — keep in sync.

export type Category =
  | "results" | "M&A" | "fund_raise" | "management_change" | "litigation"
  | "insider_trading" | "earnings_call" | "investor_meetings" | "credit_rating"
  | "dividend" | "bonus_split" | "capex" | "press_release" | "postal_ballot"
  | "agm_egm" | "pledging" | "unclassified";

export type Priority = "critical" | "high" | "normal" | "routine";

export interface Company {
  ticker: string;
  name: string;
  sector: string;
  in_portfolio: boolean;
}

export interface Position {
  company: string;
  ticker: string | null;
  title: string;
  start: number;
  end: number | null;
}

export interface Education {
  school: string;
  degree: string;
  start: number;
  end: number;
}

export interface Relationship {
  context: string;
  strength: number;
  last_contact: string | null;
}

export interface Person {
  id: string;
  name: string;
  headline: string;
  positions: Position[];
  education: Education[];
  expertise: string[];
  relationship: Relationship | null;
  synthetic: boolean;
}

export interface NetworkHint {
  person_id: string;
  name: string;
  headline: string;
  reason: string;
  degree: 1 | 2;
  via: string | null;
  strength: number;
}

export interface ReconnectNudge {
  person: Person;
  reason: string;
  days_since_contact: number | null;
}

export interface ThemeGroup {
  theme: string;
  people: NetworkHint[];
}

export interface MetricRow {
  metric: "Revenue" | "EBITDA" | "PBT" | "PAT";
  value: number;
  qoq_pct: number | null;
  yoy_pct: number | null;
}

export interface ResultsCut {
  period: string;
  unit: string;
  rows: MetricRow[];
}

export interface PushItem {
  id: string;
  kind: "announcement" | "price_move" | "volume_spike";
  ticker: string;
  company_name: string;
  category: Category | null;
  priority: Priority;
  score: number;
  title: string;
  summary: string | null;
  at: string;
  source_url: string | null;
  change_pct: number | null;
  results: ResultsCut | null;
  person: Person | null;
  network: NetworkHint[];
  synthetic: boolean;
}

export interface RoutineGroup {
  category: Category;
  count: number;
  items: PushItem[];
}

export interface Digest {
  window_hours: number;
  generated_at: string;
  attention: PushItem[];
  moves: PushItem[];
  routine: RoutineGroup[];
}

export interface AlertRules {
  price_move_pct: number;
  volume_multiple: number;
  volume_lookback_days: number;
  categories: Category[];
}

export type SectionKey =
  | "business" | "financials" | "trajectory" | "balance_sheet"
  | "cash_quality" | "narrative_vs_numbers" | "guidance" | "bull_bear";

export interface Citation {
  doc: string;
  page: number | null;
  url: string | null;
}

export interface ResearchSection {
  key: SectionKey;
  title: string;
  status: "ready" | "pending";
  body: string | null;
  citations: Citation[];
}

export interface GuidanceCheck {
  quarter: string;
  promised: string;
  delivered: string;
  verdict: "beat" | "met" | "missed" | "unclear";
  citations: Citation[];
}

export interface ResearchReport {
  company: Company;
  sections: ResearchSection[];
  guidance_vs_delivery: GuidanceCheck[];
  network: NetworkHint[];
  generated_at: string;
}
