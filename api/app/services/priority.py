"""Ranking: what earns the investor's attention, and what gets collapsed."""

from __future__ import annotations

from app.models import AlertRules, Category, Priority
from app.services.taxonomy import BASE_WEIGHT

ROUTINE_BELOW = 35


def score(category: Category, rules: AlertRules, *, has_network: bool, has_enrichment: bool) -> float:
    s = float(BASE_WEIGHT[category])
    if category in rules.categories:
        s += 10  # the investor said they care about this type
    if has_network:
        s += 5  # someone they know can explain it → more actionable
    if has_enrichment:
        s += 2  # we have numbers / a bio to show, not just a link
    return min(s, 100.0)


def bucket(s: float) -> Priority:
    if s >= 95:
        return "critical"
    if s >= 70:
        return "high"
    if s >= ROUTINE_BELOW:
        return "normal"
    return "routine"


def move_score(change_pct: float | None, volume_multiple: float | None, rules: AlertRules) -> float:
    """EOD triggers: how far past the investor's own threshold did it go?"""
    over = 0.0
    if change_pct is not None and rules.price_move_pct:
        over = max(over, abs(change_pct) / rules.price_move_pct)
    if volume_multiple is not None and rules.volume_multiple:
        over = max(over, volume_multiple / rules.volume_multiple)
    return min(60 + 20 * over, 100.0)
