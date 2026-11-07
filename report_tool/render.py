"""Render a BookingSummary as a plain-text report. Passenger names are masked unless show_names."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from report_tool.loader import Booking, SkippedRow
from report_tool.privacy import display_name
from report_tool.summary import BookingSummary


def money(amount: Decimal) -> str:
    return f"${amount:,.2f}"


def _date(value: dt.date | None) -> str:
    return value.isoformat() if value else "no date"


def _loyalty(value: bool | None) -> str:
    return {True: "Yes", False: "No", None: "Unknown"}[value]


def _booking_line(booking: Booking, with_price: bool, show_names: bool) -> str:
    parts = [
        booking.ticket_id,
        display_name(booking.passenger, show_names),
        booking.route,
        booking.ticket_class,
    ]
    if with_price:
        parts.append(money(booking.net_price))
    parts.append(_date(booking.date))
    if with_price:
        parts.append(f"Loyalty: {_loyalty(booking.loyalty)}")
    return " | ".join(parts)


def render_text(
    summary: BookingSummary,
    skipped: list[SkippedRow],
    source: str,
    generated_at: dt.datetime,
    show_names: bool = False,
) -> str:
    lines: list[str] = [
        "TRAIN BOOKINGS SUMMARY",
        f"Source: {source}",
        f"Generated: {generated_at:%Y-%m-%d %H:%M:%S}",
        f"Rows read: {summary.valid_bookings + len(skipped)} "
        f"({summary.valid_bookings} valid, {len(skipped)} skipped)",
        "",
    ]
    if skipped:
        lines += [
            f"WARNING: {len(skipped)} row(s) were skipped and are not in these totals. See SKIPPED ROWS.",
            "",
        ]

    lines += [
        "OVERVIEW",
        f"Net revenue:          {money(summary.net_revenue)}",
        f"Discounts given:      {money(summary.total_discount)}",
        f"Confirmed tickets:    {summary.confirmed_tickets}",
        f"Average net ticket:   {money(summary.average_net_ticket)}",
        f"Cancellations:        {summary.cancellations} ({summary.cancellation_rate:.1%} of valid bookings)",
        f"Loyalty members:      {summary.loyalty_members}",
        f"Non-loyalty members:  {summary.non_loyalty_members}",
    ]
    if summary.loyalty_unknown:
        lines.append(f"Loyalty unknown:      {summary.loyalty_unknown}")
    lines.append("")

    lines.append("CONFIRMED TICKETS BY CLASS")
    for ticket_class, count in summary.by_class.most_common():
        lines.append(f"{ticket_class}: {count}")
    lines.append("")

    lines.append("BOOKINGS BY ROUTE (busiest first)")
    for route, counts in summary.routes_by_volume():
        lines.append(f"{route}: {counts.confirmed} confirmed, {counts.cancelled} cancelled")
    lines.append("")

    lines.append("CONFIRMED BOOKINGS")
    lines += [
        f"{i}. {_booking_line(b, with_price=True, show_names=show_names)}"
        for i, b in enumerate(summary.confirmed, 1)
    ]
    lines.append("")

    lines.append("CANCELLED BOOKINGS")
    lines += [
        f"{i}. {_booking_line(b, with_price=False, show_names=show_names)}"
        for i, b in enumerate(summary.cancelled, 1)
    ]

    if skipped:
        lines += ["", "SKIPPED ROWS"]
        for item in skipped:
            ticket = item.ticket_id or "no ticket ID"
            lines.append(f"Row {item.row} ({ticket}): {item.reason}, found {item.value}")

    return "\n".join(lines) + "\n"
