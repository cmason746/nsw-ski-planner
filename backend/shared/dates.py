"""
Sydney-local "today" — used by both the ingest (which day is day 0 when we slice the
forecast) and the API (dropping any past day at read time).

NSW ski season is winter (Jun–Sep), which is always AEST = UTC+10 with no daylight
saving, so a fixed offset is correct for the app's whole operating window and keeps the
backend dependency-free (no `tzdata` bundle needed for `zoneinfo`). Lambda's own clock is
UTC, which is why a plain `date.today()` reads yesterday during the first 10 hours of a
Sydney day.
"""

from datetime import datetime, timezone, timedelta

AEST = timezone(timedelta(hours=10))  # UTC+10 — NSW ski season, no DST


def sydney_today() -> str:
    """Today's date in Sydney (AEST) as an ISO string, e.g. '2026-08-16'."""
    return datetime.now(AEST).date().isoformat()
