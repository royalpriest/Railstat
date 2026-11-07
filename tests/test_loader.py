import datetime as dt
from decimal import Decimal

import pytest

from report_tool.loader import (
    WorkbookError,
    load_bookings,
    parse_discount,
    parse_money,
)


def test_clean_rows_load(make_workbook):
    path = make_workbook(
        [
            [
                "TB-1",
                "Ann Lee",
                "Toronto-Ottawa",
                "Economy",
                100,
                "Confirmed ",
                dt.datetime(2026, 9, 8),
                10,
                "Yes",
            ],
            ["TB-2", "Bo Chan", "Toronto-Ottawa", "First", 200, "cancelled", "2026-09-09", 0, "no"],
        ]
    )
    result = load_bookings(path)
    assert result.skipped == []
    first, second = result.bookings
    assert first.status == "confirmed"
    assert first.price == Decimal("100.00")
    assert first.net_price == Decimal("90.00")
    assert first.date == dt.date(2026, 9, 8)
    assert first.loyalty is True
    assert second.status == "cancelled"
    assert second.date == dt.date(2026, 9, 9)
    assert second.loyalty is False


def test_bad_rows_are_skipped_with_reasons_not_fatal(make_workbook):
    path = make_workbook(
        [
            ["TB-1", "Ann Lee", "A-B", "Economy", 100, "Confirmed", None, 0, "Yes"],
            ["TB-2", "Bo Chan", "A-B", "Economy", 50, None, None, 0, "No"],
            ["TB-3", "Cy Diaz", "A-B", "Economy", "TBD", "Confirmed", None, 0, "No"],
            ["TB-4", "Di Eng", "A-B", "Economy", 50, "Pending", None, 0, "No"],
            ["TB-5", "Ed Fox", "A-B", "Economy", 50, "Confirmed", None, 150, "No"],
            ["TB-6", None, "A-B", "Economy", 50, "Confirmed", None, 0, "No"],
        ]
    )
    result = load_bookings(path)
    assert [b.ticket_id for b in result.bookings] == ["TB-1"]
    reasons = {s.ticket_id: (s.row, s.reason) for s in result.skipped}
    assert reasons == {
        "TB-2": (3, "Status is empty"),
        "TB-3": (4, "Price is not a number"),
        "TB-4": (5, "Unknown status"),
        "TB-5": (6, "Discount is not a percentage from 0 to 100"),
        "TB-6": (7, "PassengerName is empty"),
    }
    assert result.rows_read == 6


def test_columns_are_matched_by_header_name_not_position(make_workbook):
    header = ["Status", "Price", "Route", "Class", "Passenger Name", "Ticket ID"]
    path = make_workbook([["Confirmed", 40, "A-B", "Economy", "Ann Lee", "TB-9"]], header=header)
    (booking,) = load_bookings(path).bookings
    assert booking.ticket_id == "TB-9"
    assert booking.price == Decimal("40.00")
    assert booking.discount_pct == 0
    assert booking.loyalty is None


def test_missing_required_column_is_a_clear_error(make_workbook):
    path = make_workbook(
        [["TB-1", "Ann", "A-B", "Economy", 10]],
        header=["TicketID", "PassengerName", "Route", "Class", "Price"],
    )
    with pytest.raises(WorkbookError, match="status"):
        load_bookings(path)


def test_blank_rows_are_ignored(make_workbook):
    path = make_workbook([[None] * 9, ["TB-1", "Ann", "A-B", "Economy", 10, "Confirmed", None, None, None]])
    result = load_bookings(path)
    assert len(result.bookings) == 1
    assert result.skipped == []


def test_empty_sheet_and_missing_file(make_workbook, tmp_path):
    with pytest.raises(WorkbookError, match="empty"):
        load_bookings(make_workbook([], header=None))
    with pytest.raises(WorkbookError, match="not found"):
        load_bookings(tmp_path / "nope.xlsx")


def test_non_excel_file_is_a_clear_error(tmp_path):
    path = tmp_path / "notes.xlsx"
    path.write_text("not a workbook")
    with pytest.raises(WorkbookError, match="Could not open"):
        load_bookings(path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(12.5, "12.50"), ("12.50", "12.50"), ("$1,200", "1200.00"), (0, "0.00")],
)
def test_parse_money(value, expected):
    assert parse_money(value) == Decimal(expected)


@pytest.mark.parametrize("value", ["TBD", "", None, -5, True, "nan"])
def test_parse_money_rejects(value):
    with pytest.raises(ValueError):
        parse_money(value)


@pytest.mark.parametrize(
    ("value", "expected"), [(None, "0"), ("", "0"), (15, "15"), ("15%", "15"), (100, "100")]
)
def test_parse_discount(value, expected):
    assert parse_discount(value) == Decimal(expected)
