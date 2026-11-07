"""Chart geometry computed in Python so the HTML report needs no charting library."""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from report_tool.loader import Booking


def nice_max(value: float) -> float:
    """Round up to 1, 2, 2.5, 5 or 10 times a power of ten, so axis ticks read cleanly."""
    if value <= 0:
        return 1
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 2.5, 5, 10):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


def nice_axis(value: float, count: int = 4, integer: bool = False) -> float:
    """Axis maximum whose `count` equal steps are round numbers (whole numbers when `integer`)."""
    step = nice_max(value / count) if value > 0 else 1
    if integer:
        step = max(1, math.ceil(step))
    return step * count


def ticks(maximum: float, count: int = 4) -> list[float]:
    return [maximum * i / count for i in range(count + 1)]


def percent(value: float, maximum: float) -> float:
    return round(100 * value / maximum, 2) if maximum else 0.0


@dataclass(frozen=True)
class WeekPoint:
    week_start: dt.date
    revenue: Decimal
    x: float
    y: float
    labelled: bool = True


@dataclass(frozen=True)
class LineChart:
    points: list[WeekPoint]
    y_ticks: list[tuple[float, float]]  # (value, y position)
    width: int
    height: int
    left: int
    top: int
    bottom: int

    @property
    def polyline(self) -> str:
        return " ".join(f"{p.x},{p.y}" for p in self.points)

    @property
    def area_path(self) -> str:
        first, last = self.points[0], self.points[-1]
        return (
            f"M{first.x} {self.bottom} L"
            + " L".join(f"{p.x} {p.y}" for p in self.points)
            + (f" L{last.x} {self.bottom} Z")
        )

    @property
    def peak(self) -> WeekPoint:
        return max(self.points, key=lambda p: p.revenue)


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


def line_chart(
    series: list[tuple[dt.date, Decimal]], width: int = 640, height: int = 240
) -> LineChart | None:
    if len(series) < 2:
        return None
    left, right, top, bottom = 72, width - 24, 16, height - 44
    y_max = nice_axis(float(max(value for _, value in series)))
    step = (right - left) / (len(series) - 1)

    def y_of(value: float) -> float:
        return round(bottom - (bottom - top) * value / y_max, 1)

    every = math.ceil(len(series) / 8)  # at most 8 date labels on the axis
    points = [
        WeekPoint(week, value, round(left + i * step, 1), y_of(float(value)), labelled=i % every == 0)
        for i, (week, value) in enumerate(series)
    ]
    return LineChart(
        points=points,
        y_ticks=[(value, y_of(value)) for value in ticks(y_max)],
        width=width,
        height=height,
        left=left,
        top=top,
        bottom=bottom,
    )
