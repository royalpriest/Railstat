import datetime as dt
from decimal import Decimal

from report_tool.charts import line_chart, nice_axis, nice_max, weekly_revenue
from report_tool.html_report import render_html
from report_tool.loader import Booking, SkippedRow
from report_tool.summary import summarize

NOW = dt.datetime(2026, 10, 31, 14, 2)


def booking(
    ticket, status="confirmed", price="100", date=dt.date(2026, 9, 8), passenger="Ann Lee", route="A-B"
):
    return Booking(
        row=2,
        ticket_id=ticket,
        passenger=passenger,
        route=route,
        ticket_class="Economy",
        price=Decimal(price),
        status=status,
        date=date,
        discount_pct=Decimal("0"),
        loyalty=True,
    )


def render(bookings, skipped=(), **kwargs):
    return render_html(
        summarize(list(bookings)),
        list(skipped),
        source="bookings.xlsx",
        source_sha256="ab" * 32,
        generated_at=NOW,
        **kwargs,
    )


def test_spreadsheet_text_is_escaped():
    html = render([booking("<script>alert(1)</script>", route="<b>A</b>")], show_names=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;A&lt;/b&gt;" in html


def test_kpis_and_masking():
    html = render([booking("1", price="1200"), booking("2", status="cancelled")])
    assert "$1,200.00" in html
    assert "50.0%" in html
    assert "A. L••" in html and "Ann Lee" not in html
    assert "run with --show-names" in html
    assert "abab…abab" in html


def test_skipped_banner_only_when_rows_were_skipped():
    assert "skipped and" not in render([booking("1")])
    html = render([booking("1")], [SkippedRow(5, "TB-9", "Unknown status", "'Pending'")])
    assert "Warning: 1 row was skipped and is not in these totals" in html
    assert "1 × Unknown status" in html
    assert 'id="skipped"' in html


def test_trend_needs_two_weeks():
    assert "Not enough dated bookings" in render([booking("1")])
    html = render([booking("1"), booking("2", date=dt.date(2026, 9, 22))])
    assert "<polyline" in html


def test_weekly_revenue_fills_gaps_and_ignores_cancelled():
    series = weekly_revenue(
        [
            booking("1", date=dt.date(2026, 9, 9)),  # Wednesday, week of Mon 7 Sep
            booking("2", date=dt.date(2026, 9, 13)),  # Sunday, same week
            booking("3", date=dt.date(2026, 9, 21)),
            booking("4", status="cancelled", date=dt.date(2026, 9, 14)),
            booking("5", date=None),
        ]
    )
    assert series == [
        (dt.date(2026, 9, 7), Decimal("200")),
        (dt.date(2026, 9, 14), Decimal("0.00")),
        (dt.date(2026, 9, 21), Decimal("100")),
    ]


def test_line_chart_geometry():
    chart = line_chart([(dt.date(2026, 9, 7), Decimal("1000")), (dt.date(2026, 9, 14), Decimal("2000"))])
    assert [p.y for p in chart.points] == [chart.bottom - (chart.bottom - chart.top) / 2, chart.top]
    assert chart.peak.revenue == Decimal("2000")


def test_nice_max():
    assert [nice_max(v) for v in (0, 7, 73, 118, 2831.4, 10)] == [1, 10, 100, 200, 5000, 10]


def test_nice_axis_gives_round_steps():
    assert nice_axis(25, integer=True) == 40  # ticks 0, 10, 20, 30, 40
    assert nice_axis(3, integer=True) == 4  # never fractional ticks for counts
    assert nice_axis(1530.57) == 2000
    assert nice_axis(0, integer=True) == 4
