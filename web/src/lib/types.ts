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
  start: number | null;
  end: number | null;
}

export interface Education {
  school: string;
  degree: string;
  start: number | null;
  end: number | null;
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
  bio: string | null;
  positions: Position[];
  education: Education[];
  expertise: string[];
  relationship: Relationship | null;
  synthetic: boolean;
  source: "synthetic" | "linkedin" | "manual" | "company" | "filing";
  linkedin_url: string | null;
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
  | "cash_quality" | "narrative_vs_numbers" | "guidance" | "bull_bear" | "shareholding";

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
  fundamentals: Fundamentals | null;
  position: Holding | null;
  sections: ResearchSection[];
  guidance_vs_delivery: GuidanceCheck[];
  network: NetworkHint[];
  generated_at: string;
}

export type PerfPeriod = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y";
export type PriceRange = "1M" | "3M" | "6M" | "1Y" | "3Y" | "5Y";

export interface Bar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceHistory {
  ticker: string;
  range: string;
  bars: Bar[];
}

export interface Holding {
  ticker: string;
  name: string;
  sector: string;
  last_close: number | null;
  as_of: string | null;
  day_change_pct: number | null;
  return_pct: number | null;
  spark: number[];
  qty: number;
  avg_cost: number | null;
  value: number | null;
  weight_pct: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  period_pnl: number | null;
  day_pnl: number | null;
}

export interface PortfolioPerformance {
  period: PerfPeriod;
  as_of: string | null;
  portfolio_return_pct: number | null;
  weighting: "value" | "equal";
  total_value: number | null;
  total_cost: number | null;
  total_pnl: number | null;
  day_pnl: number | null;
  period_pnl: number | null;
  benchmark_name: string;
  benchmark_return_pct: number | null;
  benchmark_spark: number[];
  up: number;
  down: number;
  holdings: Holding[];
}

export interface Point {
  period: string;
  value: number | null;
}

export interface Series {
  key: string;
  name: string;
  unit: "₹ cr" | "%" | "days" | "x" | "₹";
  points: Point[];
}

export interface Metric {
  label: string;
  value: string;
  note: string | null;
}

export interface Signal {
  section: "financials" | "trajectory" | "balance_sheet" | "cash_quality" | "shareholding";
  tone: "positive" | "negative" | "neutral";
  text: string;
}

export interface Fundamentals {
  ticker: string;
  name: string;
  is_lender: boolean;
  view: string;
  about: string | null;
  source_url: string;
  updated_at: string;
  snapshot: Metric[];
  annual: Series[];
  quarterly: Series[];
  shareholding: Series[];
  signals: Signal[];
}

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
}

export interface PersonIn {
  name: string;
  current_title?: string;
  current_company?: string;
  past_roles: Position[];
  education: Education[];
  context?: string;
  strength: number;
  last_contact?: string | null;
  expertise: string[];
  linkedin_url?: string;
}

export interface CompanyLink {
  ticker: string;
  name: string;
  count: number;
  in_portfolio: boolean;
}

export interface ImportResult {
  total: number;
  added: number;
  updated: number;
  removed: number;
  linked: CompanyLink[];
  at_portfolio: number;
}

export interface CompanyPerson {
  id: string;
  ticker: string;
  name: string;
  role: string;
  kind: "executive" | "director" | "independent";
  status: "current" | "former";
  since: string | null;
  year_born: number | null;
  sources: string[];
  as_of: string | null;
  connection: NetworkHint | null;
  paths: NetworkHint[];
}

export interface CompanyPeopleSummary {
  ticker: string;
  name: string;
  people: number;
  connections: number;
}

export interface Cite {
  doc: string;
  page: number | null;
}

export interface SourceDoc {
  id: string;
  kind: "transcript" | "presentation" | "annual_report" | "filing";
  title: string;
  period: string | null;
  url: string;
  pages: number;
  used_pages: number;
}

export interface Movement {
  date: string;
  kind: "financial" | "event" | "people" | "ownership" | "market";
  title: string;
  detail: string | null;
  tone: "positive" | "negative" | "neutral";
  category: Category | null;
  reaction_pct: number | null;
  cites: Cite[];
}

export interface CitedPoint {
  text: string;
  cites: Cite[];
}

export interface GuidanceItem {
  metric: string;
  value: string;
  horizon: string | null;
  cites: Cite[];
}

export interface PromiseCheck {
  quarter: string;
  promised: string;
  delivered: string;
  verdict: "beat" | "met" | "missed" | "unclear";
  cites: Cite[];
}

export interface Theme {
  title: string;
  detail: string;
  cites: Cite[];
}

export interface Question {
  question: string;
  why: string | null;
  ask: NetworkHint | null;
}

export interface DeepResearch {
  ticker: string;
  name: string;
  generated_at: string;
  sources: SourceDoc[];
  movements: Movement[];
  summary: string | null;
  promised_vs_delivered: PromiseCheck[];
  guidance: GuidanceItem[];
  themes: Theme[];
  risks: Theme[];
  bull: CitedPoint[];
  bear: CitedPoint[];
  questions: Question[];
  network: NetworkHint[];
  stats: {
    seconds: number;
    documents: number;
    pages_read: number;
    llm: { calls: number; cached: number; tokens_in: number; tokens_out: number; models?: Record<string, number> };
    llm_available: boolean;
  };
  notes: string[];
}

export interface ResearchStep {
  key: string;
  label: string;
  status: "pending" | "running" | "done" | "skipped" | "error";
  detail: string | null;
}

export interface ResearchJob {
  id: string;
  ticker: string;
  status: "queued" | "running" | "done" | "error";
  steps: ResearchStep[];
  started_at: string;
  finished_at: string | null;
  error: string | null;
  result: DeepResearch | null;
}
