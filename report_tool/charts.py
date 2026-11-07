"""Series helpers shared by the web app's preview chart."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal

from report_tool.loader import Booking


def weekly_revenue(bookings: list[Booking]) -> list[tuple[dt.date, Decimal]]:
    """Net revenue of confirmed, dated bookings per week (weeks start Monday), gaps filled with zero."""
    totals: dict[dt.date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for booking in bookings:
        if booking.status == "confirmed" and booking.date:
            totals[booking.date - dt.timedelta(days=booking.date.weekday())] += booking.net_price
    if not totals:
        return []
    week, last = min(totals), max(totals)
    series = []
    while week <= last:
        series.append((week, totals.get(week, Decimal("0.00"))))
        week += dt.timedelta(weeks=1)
    return series
