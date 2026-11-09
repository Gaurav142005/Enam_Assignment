"""API contract. Mirrored by hand in web/src/lib/types.ts — keep the two in sync."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# Taxonomy from the ENAM reference doc (section 1). Used for classification + priority.
Category = Literal[
    "results",
    "M&A",
    "fund_raise",
    "management_change",
    "litigation",
    "insider_trading",
    "earnings_call",
    "investor_meetings",
    "credit_rating",
    "dividend",
    "bonus_split",
    "capex",
    "press_release",
    "postal_ballot",
    "agm_egm",
    "pledging",
    "unclassified",
]

Priority = Literal["critical", "high", "normal", "routine"]


# ── Companies ──────────────────────────────────────────────────────────────


class Company(BaseModel):
    ticker: str  # NSE symbol, no suffix (e.g. "POLYCAB")
    name: str
    sector: str
    in_portfolio: bool = False


# ── Network (shared by every layer) ───────────────────────────────────────


class Position(BaseModel):
    company: str
    ticker: str | None = None  # set when the employer is a listed company we track
    title: str
    start: int | None = None  # year; None when the source doesn't say
    end: int | None = None  # None = current (or unknown when start is None)


class Education(BaseModel):
    school: str
    degree: str = ""
    start: int | None = None
    end: int | None = None


class Relationship(BaseModel):
    context: str  # how the investor knows them: "IIT Kanpur batchmate", "met at Dixon plant visit"
    strength: float = Field(ge=0, le=1)
    last_contact: date | None = None


class Person(BaseModel):
    id: str
    name: str
    headline: str
    bio: str | None = None  # short profile, e.g. from the filing that announced their appointment
    positions: list[Position] = []
    education: list[Education] = []
    expertise: list[str] = []
    relationship: Relationship | None = None  # None = not in the investor's network (e.g. a person in a filing)
    synthetic: bool = True
    source: Literal["synthetic", "linkedin", "manual", "company", "filing"] = "synthetic"
    linkedin_url: str | None = None


class NetworkHint(BaseModel):
    """The inline 'who can help me understand this' chip that rides on Push and Pull items."""

    person_id: str
    name: str
    headline: str
    reason: str
    degree: Literal[1, 2]
    via: str | None = None  # intermediary's name when degree == 2
    strength: float = Field(ge=0, le=1)


class ReconnectNudge(BaseModel):
    person: Person
    reason: str
    days_since_contact: int | None


class ThemeGroup(BaseModel):
    theme: str
    people: list[NetworkHint]


# ── Push ──────────────────────────────────────────────────────────────────


class MetricRow(BaseModel):
    metric: Literal["Revenue", "EBITDA", "PBT", "PAT"]
    value: float  # ₹ crore
    qoq_pct: float | None
    yoy_pct: float | None


class ResultsCut(BaseModel):
    period: str  # "Q2 FY27"
    unit: str = "₹ cr"
    rows: list[MetricRow]


class PushItem(BaseModel):
    id: str
    kind: Literal["announcement", "price_move", "volume_spike"]
    ticker: str
    company_name: str
    category: Category | None = None
    priority: Priority
    score: float
    title: str
    summary: str | None = None  # one-liner; omitted where the title says it all
    at: datetime
    source_url: str | None = None
    change_pct: float | None = None  # EOD moves: day's close-to-close change
    results: ResultsCut | None = None  # quarterly results → headline numbers
    person: Person | None = None  # management change → who the incoming person is
    network: list[NetworkHint] = []
    synthetic: bool = False


class RoutineGroup(BaseModel):
    category: Category
    count: int
    items: list[PushItem]


class Digest(BaseModel):
    window_hours: int
    generated_at: datetime
    attention: list[PushItem]  # ranked: what earns the investor's time
    moves: list[PushItem]  # EOD price/volume triggers
    routine: list[RoutineGroup]  # collapsed by default


class AlertRules(BaseModel):
    price_move_pct: float = 5.0
    volume_multiple: float = 2.0
    volume_lookback_days: int = 20
    categories: list[Category] = ["results", "M&A", "management_change", "litigation", "capex", "pledging"]


# ── Pull ──────────────────────────────────────────────────────────────────

SectionKey = Literal[
    "business",
    "financials",
    "trajectory",
    "balance_sheet",
    "cash_quality",
    "narrative_vs_numbers",
    "guidance",
    "bull_bear",
    "shareholding",
]


class Citation(BaseModel):
    doc: str  # "Q1 FY27 concall transcript"
    page: int | None = None
    url: str | None = None


class ResearchSection(BaseModel):
    key: SectionKey
    title: str
    status: Literal["ready", "pending"]
    body: str | None = None
    citations: list[Citation] = []


class GuidanceCheck(BaseModel):
    quarter: str
    promised: str
    delivered: str
    verdict: Literal["beat", "met", "missed", "unclear"]
    citations: list[Citation] = []


class ResearchReport(BaseModel):
    company: Company
    fundamentals: "Fundamentals | None" = None
    position: "Holding | None" = None  # the investor's own holding, if any
    sections: list[ResearchSection]
    guidance_vs_delivery: list[GuidanceCheck] = []
    network: list[NetworkHint] = []
    generated_at: datetime


# ── Market ────────────────────────────────────────────────────────────────

PerfPeriod = Literal["1D", "1W", "1M", "3M", "6M", "1Y"]


class Bar(BaseModel):
    time: str  # YYYY-MM-DD (session date)
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceHistory(BaseModel):
    ticker: str
    range: str
    bars: list[Bar]


class Holding(BaseModel):
    ticker: str
    name: str
    sector: str
    last_close: float | None
    as_of: str | None
    day_change_pct: float | None
    return_pct: float | None  # price return over the selected period
    spark: list[float]
    qty: int = 0
    avg_cost: float | None = None
    value: float | None = None  # qty × last close, ₹
    weight_pct: float | None = None  # share of portfolio value
    pnl: float | None = None  # unrealised, ₹ vs avg cost
    pnl_pct: float | None = None
    period_pnl: float | None = None  # ₹ gained/lost over the selected period
    day_pnl: float | None = None  # ₹ change on the last session


class PortfolioPerformance(BaseModel):
    period: PerfPeriod
    as_of: str | None
    portfolio_return_pct: float | None  # value-weighted over the period (equal-weighted if no quantities)
    weighting: Literal["value", "equal"]
    total_value: float | None
    total_cost: float | None
    total_pnl: float | None
    day_pnl: float | None
    period_pnl: float | None
    benchmark_name: str
    benchmark_return_pct: float | None
    benchmark_spark: list[float]
    up: int
    down: int
    holdings: list[Holding]  # sorted best → worst


# ── News (secondary source: context only, never research input) ───────────


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime


# ── Fundamentals (deterministic, from standardised filings data) ──────────


class Point(BaseModel):
    period: str  # "Mar 2026" (FY), "Sep 2026" (quarter), "TTM"
    value: float | None


class Series(BaseModel):
    key: str
    name: str
    unit: Literal["₹ cr", "%", "days", "x", "₹"]
    points: list[Point]


class Metric(BaseModel):
    label: str
    value: str
    note: str | None = None


class Signal(BaseModel):
    section: Literal["financials", "trajectory", "balance_sheet", "cash_quality", "shareholding"]
    tone: Literal["positive", "negative", "neutral"]
    text: str


class Fundamentals(BaseModel):
    ticker: str
    name: str
    is_lender: bool
    view: str  # consolidated | standalone
    about: str | None
    source_url: str
    updated_at: str
    snapshot: list[Metric]
    annual: list[Series]
    quarterly: list[Series]
    shareholding: list[Series]
    signals: list[Signal]


ResearchReport.model_rebuild()



# ── Connections & company people ──────────────────────────────────────────


class PersonIn(BaseModel):
    """A connection added by hand."""

    name: str = Field(min_length=2, max_length=120)
    current_title: str | None = None
    current_company: str | None = None
    past_roles: list[Position] = []
    education: list[Education] = []
    context: str | None = None  # how you know them
    strength: float = Field(0.6, ge=0, le=1)
    last_contact: date | None = None
    expertise: list[str] = []
    linkedin_url: str | None = None


class CompanyLink(BaseModel):
    ticker: str
    name: str
    count: int
    in_portfolio: bool


class ImportResult(BaseModel):
    total: int
    added: int
    updated: int
    removed: int
    linked: list[CompanyLink]  # listed employers we recognised, most connections first
    at_portfolio: int  # connections who work / worked at a portfolio company


class CompanyPerson(BaseModel):
    id: str
    ticker: str
    name: str
    role: str
    kind: Literal["executive", "director", "independent"]
    status: Literal["current", "former"]
    since: str | None = None
    year_born: int | None = None
    sources: list[str]
    as_of: str | None = None
    connection: NetworkHint | None = None  # they ARE in your network
    paths: list[NetworkHint] = []  # who in your network can reach them


class CompanyPeopleSummary(BaseModel):
    ticker: str
    name: str
    people: int
    connections: int  # your connections who work / worked there


# ── Deep research (Pull, on demand, 30–60 s) ──────────────────────────────


class Cite(BaseModel):
    doc: str  # short id of a SourceDoc, e.g. "T1"
    page: int | None = None


class SourceDoc(BaseModel):
    id: str  # T1..T4 transcripts, P1..P2 presentations, A1 annual report, F1.. filings
    kind: Literal["transcript", "presentation", "annual_report", "filing"]
    title: str
    period: str | None = None
    url: str
    pages: int = 0
    used_pages: int = 0  # pages actually sent to a model (annual reports are pre-filtered)


class Movement(BaseModel):
    date: str  # YYYY-MM-DD (or quarter end)
    kind: Literal["financial", "event", "people", "ownership", "market"]
    title: str
    detail: str | None = None
    tone: Literal["positive", "negative", "neutral"] = "neutral"
    category: Category | None = None
    reaction_pct: float | None = None  # stock move on the session the market first saw it
    cites: list[Cite] = []
    source_id: str | None = None  # announcement id, for events


class Point_(BaseModel):
    text: str
    cites: list[Cite] = []


class GuidanceItem(BaseModel):
    metric: str
    value: str
    horizon: str | None = None
    cites: list[Cite] = []


class PromiseCheck(BaseModel):
    quarter: str
    promised: str
    delivered: str
    verdict: Literal["beat", "met", "missed", "unclear"]
    cites: list[Cite] = []


class Theme(BaseModel):
    title: str
    detail: str
    cites: list[Cite] = []


class Question(BaseModel):
    question: str
    why: str | None = None
    ask: NetworkHint | None = None  # who in your network could answer it


class ResearchStats(BaseModel):
    seconds: float
    documents: int
    pages_read: int
    llm: dict  # Usage.as_dict()
    llm_available: bool


class DeepResearch(BaseModel):
    ticker: str
    name: str
    generated_at: datetime
    sources: list[SourceDoc]
    movements: list[Movement]  # newest first
    summary: str | None = None
    promised_vs_delivered: list[PromiseCheck] = []
    guidance: list[GuidanceItem] = []
    themes: list[Theme] = []
    risks: list[Theme] = []
    bull: list[Point_] = []
    bear: list[Point_] = []
    questions: list[Question] = []
    network: list[NetworkHint] = []
    stats: ResearchStats
    notes: list[str] = []  # what couldn't be done and why


class ResearchStep(BaseModel):
    key: str
    label: str
    status: Literal["pending", "running", "done", "skipped", "error"] = "pending"
    detail: str | None = None


class ResearchJob(BaseModel):
    id: str
    ticker: str
    status: Literal["queued", "running", "done", "error"]
    steps: list[ResearchStep]
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None
    result: DeepResearch | None = None
