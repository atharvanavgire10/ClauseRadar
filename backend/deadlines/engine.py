"""Deterministic temporal rules engine — pure functions, no I/O, no LLM.

All date math uses timezone-aware datetimes; day arithmetic is done on dates
in the workspace timezone (UTC by default). Business days skip Sat/Sun.
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DUE_SOON_DAYS = 7
DEFAULT_RENEWAL_NOTICE_DAYS = 30
DEFAULT_RECURRING_OCCURRENCES = 6

# Frequency → months per occurrence (WEEKLY/DAILY handled as day steps).
MONTHS_PER_FREQUENCY = {
    "MONTHLY": 1,
    "QUARTERLY": 3,
    "SEMI_ANNUAL": 6,
    "ANNUAL": 12,
}
DAY_STEP_FREQUENCY = {"DAILY": 1, "WEEKLY": 7}
RECURRING_FREQUENCIES = set(MONTHS_PER_FREQUENCY) | set(DAY_STEP_FREQUENCY)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
LONG_DATE_RE = re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b", re.IGNORECASE)
RELATIVE_RE = re.compile(
    r"\bwithin\s+(\d+)\s+(hour|day|week|month|year)s?\b|\b(\d+)\s+days?\s+(before|after|prior to|following)\b",
    re.IGNORECASE,
)


def add_business_days(day: date, n: int) -> date:
    """Add (or subtract) business days, skipping Saturday/Sunday."""
    if n == 0:
        return day
    step = 1 if n > 0 else -1
    remaining = abs(n)
    current = day
    while remaining:
        current += timedelta(days=step)
        if current.weekday() < 5:
            remaining -= 1
    return current


def shift(day: date, days: int, *, direction: str = "after", business: bool = False) -> date:
    """Shift a date by N days before/after (calendar or business days)."""
    if direction not in ("before", "after"):
        raise ValueError("direction must be 'before' or 'after'")
    signed = days if direction == "after" else -days
    if business:
        return add_business_days(day, signed)
    return day + timedelta(days=signed)


def parse_explicit_date(text: str) -> date | None:
    """Parse the first explicit calendar date in text. None when absent.

    Never invents dates: unparseable text yields None and callers must skip.
    """
    m = ISO_DATE_RE.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = LONG_DATE_RE.search(text)
    if m:
        try:
            return date(int(m.group(3)), _MONTHS[m.group(2).lower()[:3]], int(m.group(1)))
        except ValueError:
            return None
    return None


def parse_relative(text: str) -> dict | None:
    """Parse relative offsets like 'within 30 days' or '60 days before'.

    Returns {days, unit, direction} or None. Hours are normalized to 0 days
    with hours kept for display (deadlines resolve to dates).
    """
    m = RELATIVE_RE.search(text)
    if not m:
        return None
    if m.group(1):
        amount, unit = int(m.group(1)), m.group(2).lower()
        days = {"hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}[unit] * amount
        return {"days": days, "unit": unit, "direction": "after", "hours": amount if unit == "hour" else 0}
    amount, direction = int(m.group(3)), m.group(4).lower()
    return {"days": amount, "unit": "day",
            "direction": "before" if direction in ("before", "prior to") else "after", "hours": 0}


def deadline_status(due: date, today: date, *, completed: bool = False,
                    waived: bool = False, due_soon_days: int = DUE_SOON_DAYS) -> str:
    """UPCOMING | DUE_SOON | OVERDUE | COMPLETED | WAIVED — pure function."""
    if completed:
        return "COMPLETED"
    if waived:
        return "WAIVED"
    if due < today:
        return "OVERDUE"
    if due <= today + timedelta(days=due_soon_days):
        return "DUE_SOON"
    return "UPCOMING"


def renewal_notice_date(renewal: date, notice_days: int, *, business: bool = False) -> date:
    """Notice deadline for a renewal date, e.g. renewal 15 Dec 2026 minus 60 days."""
    return shift(renewal, notice_days, direction="before", business=business)


def ensure_aware(value: datetime, tz: str = "UTC") -> datetime:
    """Attach UTC (or given tz) to naive datetimes; pass through aware ones."""
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=ZoneInfo(tz))


def add_months(day: date, months: int) -> date:
    """Calendar-month arithmetic clamped to month end (Jan 31 + 1mo → Feb 28/29)."""
    total = day.year * 12 + (day.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    last = monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def occurrence_dates(frequency: str, anchor: date, *, today: date, count: int = DEFAULT_RECURRING_OCCURRENCES) -> list[date]:
    """Next `count` occurrence dates strictly after `today`, stepping from anchor.

    Deterministic: same (frequency, anchor) always yields the same series.
    Raises ValueError for non-recurring frequencies (ONE_TIME/CONTINUOUS/CUSTOM).
    """
    if frequency in MONTHS_PER_FREQUENCY:
        step = MONTHS_PER_FREQUENCY[frequency]
        current = anchor
        # Fast-forward past today without building unbounded lists.
        while current <= today:
            current = add_months(current, step)
        out = []
        for _ in range(count):
            out.append(current)
            current = add_months(current, step)
        return out
    if frequency in DAY_STEP_FREQUENCY:
        step = DAY_STEP_FREQUENCY[frequency]
        current = anchor
        while current <= today:
            current += timedelta(days=step)
        return [current + timedelta(days=step * i) for i in range(count)]
    raise ValueError(f"Frequency {frequency} is not recurring.")


def today_in_tz(tz: str = "UTC") -> date:
    return datetime.now(ZoneInfo(tz)).date()
