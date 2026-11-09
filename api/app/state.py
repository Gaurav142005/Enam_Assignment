"""Per-investor settings. In-memory for the prototype; SQLite row per user in the real thing."""

from app.models import AlertRules

rules = AlertRules()
