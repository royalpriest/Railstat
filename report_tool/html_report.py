"""Render a BookingSummary as one self-contained HTML file (no server, no external assets)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from jinja2 import Environment, PackageLoader, select_autoescape

from report_tool import __version__
from report_tool.charts import line_chart, nice_axis, percent, ticks, weekly_revenue
from report_tool.loader import Booking, SkippedRow
from report_tool.privacy import display_name
from report_tool.render import money
from report_tool.summary import BookingSummary

_env = Environment(
    loader=PackageLoader("report_tool", "templates"),
    autoescape=select_autoescape(["html", "j2"]),  # spreadsheet text is untrusted: always escape it
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["money"] = money


def _number(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"


def _short_money(value: float) -> str:
    if value >= 1000:
        return f"${value / 1000:,.1f}k".replace(".0k", "k")
    return f"${value:,.0f}"


def _day(value: dt.date) -> str:
    return f"{value.day} {value:%b}"


_env.filters["number"] = _number
_env.filters["day"] = _day
_env.filters["short_money"] = _short_money


@dataclass(frozen=True)
class Row:
    ticket_id: str
    passenger: str
    route: str
    ticket_class: str
    net_price: Decimal | None
    date: dt.date | None
    status: str


def _rows(bookings: list[Booking], show_names: bool) -> list[Row]:
    ordered = sorted(bookings, key=lambda b: (b.date or dt.date.max, b.row))
    return [
        Row(
            ticket_id=b.ticket_id,
            passenger=display_name(b.passenger, show_names),
            route=b.route,
            ticket_class=b.ticket_class,
            net_price=b.net_price if b.status == "confirmed" else None,
            date=b.date,
            status=b.status,
        )
        for b in ordered
    ]


def render_html(
    summary: BookingSummary,
    skipped: list[SkippedRow],
    source: str,
    source_sha256: str,
    generated_at: dt.datetime,
    show_names: bool = False,
    skipped_csv_name: str | None = None,
) -> str:
    routes = summary.routes_by_volume()
    route_max = nice_axis(max((counts.total for _, counts in routes), default=0), integer=True)
    route_bars = [
        {
            "name": name,
            "confirmed": counts.confirmed,
            "cancelled": counts.cancelled,
            "confirmed_pct": percent(counts.confirmed, route_max),
            "cancelled_pct": percent(counts.cancelled, route_max),
        }
        for name, counts in routes
    ]
    classes = summary.by_class.most_common()
    class_max = nice_axis(max((count for _, count in classes), default=0), integer=True)
    class_bars = [{"name": name, "count": count, "pct": percent(count, class_max)} for name, count in classes]

    loyalty_known = summary.loyalty_members + summary.non_loyalty_members
    template = _env.get_template("report.html.j2")
    return template.render(
        s=summary,
        skipped=skipped,
        skipped_reasons=_reason_counts(skipped),
        skipped_csv_name=skipped_csv_name,
        source=source,
        source_hash=f"{source_sha256[:4]}…{source_sha256[-4:]}",
        generated_at=generated_at,
        rows_read=summary.valid_bookings + len(skipped),
        loyalty_pct=percent(summary.loyalty_members, loyalty_known),
        loyalty_known=loyalty_known,
        route_bars=route_bars,
        route_ticks=ticks(route_max),
        class_bars=class_bars,
        class_ticks=ticks(class_max),
        line=line_chart(weekly_revenue(summary.confirmed)),
        rows=_rows(summary.confirmed + summary.cancelled, show_names),
        show_names=show_names,
        version=__version__,
    )


def _reason_counts(skipped: list[SkippedRow]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in skipped:
        counts[item.reason] = counts.get(item.reason, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])
