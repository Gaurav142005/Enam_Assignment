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
    sections: list[ResearchSection]
    guidance_vs_delivery: list[GuidanceCheck] = []
    network: list[NetworkHint] = []
    generated_at: datetime
