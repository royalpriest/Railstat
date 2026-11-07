from pathlib import Path

import openpyxl
import pytest

HEADER = [
    "TicketID",
    "PassengerName",
    "Route",
    "Class",
    "Price",
    "Status",
    "Date",
    "DiscountApplied",
    "LoyaltyMember",
]


@pytest.fixture
def make_workbook(tmp_path: Path):
    """Write rows (header first) to an .xlsx file and return its path."""

    def _make(
        rows: list[list[object]], header: list[str] | None = HEADER, name: str = "bookings.xlsx"
    ) -> Path:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        if header is not None:
            sheet.append(header)
        for row in rows:
            sheet.append(row)
        path = tmp_path / name
        workbook.save(path)
        return path

    return _make
