import datetime as dt
import json
import re
from decimal import Decimal

from report_tool.charts import weekly_revenue
from report_tool.html_report import all_weeks, dashboard_data, render_html
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
    assert "<b>A</b>" not in html
    # The embedded data escapes < and > so spreadsheet text can't close the script tag.
    assert "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e" in html
    assert embedded(html)["bookings"][0]["t"] == "<script>alert(1)</script>"


def embedded(html):
    match = re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S)
    return json.loads(match.group(1))


def test_kpis_and_masking():
    html = render([booking("1", price="1200"), booking("2", status="cancelled")])
    assert "$1,200.00" in html
    assert "50.0%" in html
    assert embedded(html)["bookings"][0]["p"] == "A. L••" and "Ann Lee" not in html
    assert "abab…abab" in html
    assert "run with --show-names" in html
    assert "Space Mono" in html and 'id="theme-toggle"' in html
    assert "All 2 rows used." in html


def test_upload_link_only_in_web_app_mode():
    assert 'href="/"' not in render([booking("1")])
    assert 'href="/"' in render([booking("1")], upload_url="/")


def test_dashboard_data_is_compact_and_masked():
    data = dashboard_data(
        [
            booking("1", price="85.50", date=dt.date(2026, 9, 9)),
            booking("2", status="cancelled", date=dt.date(2026, 9, 23)),
            booking("3", date=None),
        ],
        show_names=False,
    )
    assert data["weeks"] == ["2026-09-07", "2026-09-14", "2026-09-21"]
    first = data["bookings"][0]
    assert first == {
        "t": "1",
        "p": "A. L••",
        "r": "A-B",
        "c": "Economy",
        "s": "confirmed",
        "d": "2026-09-09",
        "w": 0,
        "price": 8550,
        "disc": 0.0,
        "net": 8550,
        "loy": True,
    }
    assert data["bookings"][1]["w"] == 2
    assert data["bookings"][2]["w"] is None  # undated bookings sort last


def test_discount_is_kept_in_cents():
    b = Booking(
        row=2,
        ticket_id="1",
        passenger="A",
        route="R",
        ticket_class="E",
        price=Decimal("85.50"),
        status="confirmed",
        date=None,
        discount_pct=Decimal("10"),
        loyalty=None,
    )
    row = dashboard_data([b], show_names=True)["bookings"][0]
    assert (row["price"], row["net"], row["disc"]) == (8550, 7695, 10.0)


def test_all_weeks_fills_gaps():
    assert all_weeks([booking("1", date=dt.date(2026, 9, 13)), booking("2", date=dt.date(2026, 9, 28))]) == [
        dt.date(2026, 9, 7),
        dt.date(2026, 9, 14),
        dt.date(2026, 9, 21),
        dt.date(2026, 9, 28),
    ]
    assert all_weeks([booking("1", date=None)]) == []


def test_skipped_banner_only_when_rows_were_skipped():
    assert "skipped and" not in render([booking("1")])
    html = render([booking("1")], [SkippedRow(5, "TB-9", "Unknown status", "'Pending'")])
    assert "Warning: 1 row was skipped and is not in these totals" in html
    assert "1 × Unknown status" in html
    assert 'id="skipped"' in html


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
