import datetime as dt

from report_tool.cli import EXIT_BAD_INPUT, EXIT_NO_BOOKINGS, EXIT_OK, main

NOW = dt.datetime(2026, 10, 31, 14, 2, 11)

EXPECTED_REPORT = """\
TRAIN BOOKINGS SUMMARY
Source: bookings.xlsx
Generated: 2026-10-31 14:02:11
Rows read: 3 (2 valid, 1 skipped)

WARNING: 1 row(s) were skipped and are not in these totals. See SKIPPED ROWS.

OVERVIEW
Net revenue:          $1,080.00
Discounts given:      $120.00
Confirmed tickets:    1
Average net ticket:   $1,080.00
Cancellations:        1 (50.0% of valid bookings)
Loyalty members:      1
Non-loyalty members:  0

CONFIRMED TICKETS BY CLASS
First: 1

BOOKINGS BY ROUTE (busiest first)
Toronto-Montreal: 1 confirmed, 1 cancelled

CONFIRMED BOOKINGS
1. TB-1 | A. L•• | Toronto-Montreal | First | $1,080.00 | 2026-09-08 | Loyalty: Yes

CANCELLED BOOKINGS
1. TB-2 | B. C••• | Toronto-Montreal | Economy | no date

SKIPPED ROWS
Row 4 (TB-3): Price is not a number, found '$5O'
"""


def test_writes_timestamped_text_report(make_workbook, tmp_path):
    path = make_workbook(
        [
            [
                "TB-1",
                "Ann Lee",
                "Toronto-Montreal",
                "First",
                1200,
                "Confirmed",
                dt.datetime(2026, 9, 8),
                10,
                "Yes",
            ],
            ["TB-2", "Bo Chan", "Toronto-Montreal", "Economy", 80, "Cancelled", None, 0, "No"],
            ["TB-3", "Cy Diaz", "Toronto-Montreal", "Economy", "$5O", "Confirmed", None, 0, "No"],
        ]
    )
    out = tmp_path / "out"
    assert main([str(path), "--out", str(out), "--format", "txt"], now=NOW) == EXIT_OK
    report = out / "booking_summary_20261031_140211.txt"
    assert report.read_text(encoding="utf-8") == EXPECTED_REPORT


def test_bad_path_exits_with_error(tmp_path, caplog):
    assert main([str(tmp_path / "missing.xlsx"), "--out", str(tmp_path)]) == EXIT_BAD_INPUT
    assert "File not found" in caplog.text


def test_no_valid_rows(make_workbook, tmp_path):
    path = make_workbook([["TB-1", "Ann", "A-B", "Economy", "TBD", "Confirmed", None, 0, "No"]])
    assert main([str(path), "--out", str(tmp_path / "out")]) == EXIT_NO_BOOKINGS
    assert not (tmp_path / "out").exists()


def test_prompts_for_path_when_not_given(make_workbook, tmp_path, monkeypatch):
    path = make_workbook([["TB-1", "Ann", "A-B", "Economy", 10, "Confirmed", None, 0, "Yes"]])
    monkeypatch.setattr("builtins.input", lambda _prompt: f'"{path}"')
    assert main(["--out", str(tmp_path / "out")], now=NOW) == EXIT_OK


def three_rows(make_workbook):
    return make_workbook(
        [
            [
                "TB-1",
                "Ann Lee",
                "Toronto-Montreal",
                "First",
                1200,
                "Confirmed",
                dt.datetime(2026, 9, 8),
                10,
                "Yes",
            ],
            ["TB-2", "Bo Chan", "Toronto-Montreal", "Economy", 80, "Cancelled", None, 0, "No"],
            ["@TB-3", "Cy Diaz", "Toronto-Montreal", "Economy", "TBD", "Confirmed", None, 0, "No"],
        ]
    )


def test_html_is_the_default_and_skipped_rows_csv_is_written(make_workbook, tmp_path):
    out = tmp_path / "out"
    assert main([str(three_rows(make_workbook)), "--out", str(out)], now=NOW) == EXIT_OK
    assert sorted(p.name for p in out.iterdir()) == [
        "booking_summary_20261031_140211.html",
        "booking_summary_20261031_140211_skipped_rows.csv",
    ]
    html = (out / "booking_summary_20261031_140211.html").read_text(encoding="utf-8")
    assert "1 row was skipped" in html
    assert r"A. L\u2022\u2022" in html and "Ann Lee" not in html
    csv_text = (out / "booking_summary_20261031_140211_skipped_rows.csv").read_text(encoding="utf-8")
    assert csv_text.splitlines() == [
        "excel_row,ticket_id,reason,value_found",
        "4,'@TB-3,Price is not a number,'TBD'",
    ]


def test_both_formats_and_show_names(make_workbook, tmp_path):
    out = tmp_path / "out"
    args = [str(three_rows(make_workbook)), "--out", str(out), "--format", "both", "--show-names"]
    assert main(args, now=NOW) == EXIT_OK
    for suffix in (".txt", ".html"):
        assert "Ann Lee" in (out / f"booking_summary_20261031_140211{suffix}").read_text(encoding="utf-8")
