import datetime as dt
from decimal import Decimal

from report_tool.loader import Booking
from report_tool.summary import summarize


def booking(ticket, route, status, price="100", discount="0", loyalty=True, ticket_class="Economy"):
    return Booking(
        row=2,
        ticket_id=ticket,
        passenger="Test Person",
        route=route,
        ticket_class=ticket_class,
        price=Decimal(price),
        status=status,
        date=dt.date(2026, 9, 8),
        discount_pct=Decimal(discount),
        loyalty=loyalty,
    )


def test_totals_use_exact_money():
    summary = summarize(
        [
            booking("1", "A-B", "confirmed", price="0.10", discount="0"),
            booking("2", "A-B", "confirmed", price="0.20", discount="0"),
            booking("3", "A-B", "confirmed", price="33.33", discount="15"),
        ]
    )
    # 0.1 + 0.2 is 0.30000000000000004 with floats; Decimal keeps it exact.
    assert summary.total_discount == Decimal("5.00")
    assert summary.net_revenue == Decimal("28.63")
    assert summary.average_net_ticket == Decimal("9.54")


def test_counts_routes_classes_and_loyalty():
    summary = summarize(
        [
            booking("1", "A-B", "confirmed", ticket_class="First", loyalty=True),
            booking("2", "A-B", "cancelled"),
            booking("3", "C-D", "confirmed", loyalty=False),
            booking("4", "C-D", "confirmed", loyalty=None),
            booking("5", "C-D", "confirmed", loyalty=True),
        ]
    )
    assert summary.confirmed_tickets == 4
    assert summary.cancellations == 1
    assert summary.cancellation_rate == 0.2
    assert summary.by_class == {"First": 1, "Economy": 3}
    assert (summary.loyalty_members, summary.non_loyalty_members, summary.loyalty_unknown) == (2, 1, 1)
    assert [route for route, _ in summary.routes_by_volume()] == ["C-D", "A-B"]
    assert summary.by_route["A-B"].cancelled == 1


def test_empty_input():
    summary = summarize([])
    assert summary.valid_bookings == 0
    assert summary.cancellation_rate == 0.0
    assert summary.average_net_ticket == Decimal("0.00")
