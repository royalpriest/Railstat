"""Render a BookingSummary as one self-contained HTML dashboard.

The headline numbers are rendered here. The bookings are also embedded as JSON (names already
masked unless asked otherwise) so the page can re-compute figures, charts and the table in the
browser when the reader filters by period, route or class.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from jinja2 import Environment, PackageLoader, select_autoescape

from report_tool import __version__
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


_env.filters["number"] = _number


def week_start(day: dt.date) -> dt.date:
    """Monday of the week containing `day`."""
    return day - dt.timedelta(days=day.weekday())


def all_weeks(bookings: list[Booking]) -> list[dt.date]:
    """Every week (Monday) from the first dated booking to the last, gaps included."""
    dated = [week_start(b.date) for b in bookings if b.date]
    if not dated:
        return []
    week, last = min(dated), max(dated)
    weeks = []
    while week <= last:
        weeks.append(week)
        week += dt.timedelta(weeks=1)
    return weeks


def _cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def dashboard_data(bookings: list[Booking], show_names: bool) -> dict:
    """The bookings in the compact shape the page's script reads. Money is in whole cents."""
    weeks = all_weeks(bookings)
    index = {week: i for i, week in enumerate(weeks)}
    ordered = sorted(bookings, key=lambda b: (b.date or dt.date.max, b.row))
    return {
        "weeks": [week.isoformat() for week in weeks],
        "bookings": [
            {
                "t": b.ticket_id,
                "p": display_name(b.passenger, show_names),
                "r": b.route,
                "c": b.ticket_class,
                "s": b.status,
                "d": b.date.isoformat() if b.date else None,
                "w": index[week_start(b.date)] if b.date else None,
                "price": _cents(b.price),
                "disc": float(b.discount_pct),
                "net": _cents(b.net_price),
                "loy": b.loyalty,
            }
            for b in ordered
        ],
    }


def render_html(
    summary: BookingSummary,
    skipped: list[SkippedRow],
    source: str,
    source_sha256: str,
    generated_at: dt.datetime,
    show_names: bool = False,
    skipped_csv_name: str | None = None,
    upload_url: str | None = None,
) -> str:
    """`upload_url` is set by the web app to show an "Upload another file" link."""
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
        loyalty_pct=100 * summary.loyalty_members / loyalty_known if loyalty_known else 0,
        loyalty_known=loyalty_known,
        data=dashboard_data(summary.confirmed + summary.cancelled, show_names),
        show_names=show_names,
        upload_url=upload_url,
        version=__version__,
    )


def _reason_counts(skipped: list[SkippedRow]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in skipped:
        counts[item.reason] = counts.get(item.reason, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])
