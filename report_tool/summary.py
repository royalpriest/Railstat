"""Aggregate validated bookings into report figures."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from report_tool.loader import Booking


@dataclass
class RouteCounts:
    confirmed: int = 0
    cancelled: int = 0

    @property
    def total(self) -> int:
        return self.confirmed + self.cancelled


@dataclass
class BookingSummary:
    confirmed_tickets: int = 0
    cancellations: int = 0
    net_revenue: Decimal = Decimal("0.00")
    total_discount: Decimal = Decimal("0.00")
    loyalty_members: int = 0
    non_loyalty_members: int = 0
    loyalty_unknown: int = 0
    by_class: Counter[str] = field(default_factory=Counter)
    by_route: dict[str, RouteCounts] = field(default_factory=dict)
    confirmed: list[Booking] = field(default_factory=list)
    cancelled: list[Booking] = field(default_factory=list)

    @property
    def valid_bookings(self) -> int:
        return self.confirmed_tickets + self.cancellations

    @property
    def cancellation_rate(self) -> float:
        return self.cancellations / self.valid_bookings if self.valid_bookings else 0.0

    @property
    def average_net_ticket(self) -> Decimal:
        if not self.confirmed_tickets:
            return Decimal("0.00")
        return (self.net_revenue / self.confirmed_tickets).quantize(Decimal("0.01"))

    def routes_by_volume(self) -> list[tuple[str, RouteCounts]]:
        return sorted(self.by_route.items(), key=lambda item: (-item[1].total, item[0]))


def summarize(bookings: list[Booking]) -> BookingSummary:
    summary = BookingSummary()
    for booking in bookings:
        route = summary.by_route.setdefault(booking.route, RouteCounts())
        if booking.status == "confirmed":
            summary.confirmed_tickets += 1
            summary.net_revenue += booking.net_price
            summary.total_discount += booking.discount_amount
            summary.by_class[booking.ticket_class] += 1
            route.confirmed += 1
            if booking.loyalty is True:
                summary.loyalty_members += 1
            elif booking.loyalty is False:
                summary.non_loyalty_members += 1
            else:
                summary.loyalty_unknown += 1
            summary.confirmed.append(booking)
        else:
            summary.cancellations += 1
            route.cancelled += 1
            summary.cancelled.append(booking)
    return summary
