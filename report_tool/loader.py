"""Read bookings from an Excel workbook and validate each row."""

from __future__ import annotations

import datetime as dt
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

# Internal field name -> accepted header spellings (compared case- and space-insensitively).
COLUMNS: dict[str, tuple[str, ...]] = {
    "ticket_id": ("ticketid", "ticket id", "ticket"),
    "passenger": ("passengername", "passenger name", "passenger"),
    "route": ("route",),
    "ticket_class": ("class", "ticketclass", "ticket class"),
    "price": ("price",),
    "status": ("status",),
    "date": ("date",),
    "discount": ("discountapplied", "discount applied", "discount"),
    "loyalty": ("loyaltymember", "loyalty member", "loyalty"),
}
REQUIRED = ("ticket_id", "passenger", "route", "ticket_class", "price", "status")

STATUSES = {"confirmed": "confirmed", "cancelled": "cancelled", "canceled": "cancelled"}
YES = {"yes", "y", "true", "1"}
NO = {"no", "n", "false", "0"}


class WorkbookError(Exception):
    """The workbook can't be read, or it's missing required columns."""


@dataclass(frozen=True)
class Booking:
    row: int
    ticket_id: str
    passenger: str
    route: str
    ticket_class: str
    price: Decimal
    status: str  # "confirmed" or "cancelled"
    date: dt.date | None
    discount_pct: Decimal
    loyalty: bool | None  # None when the cell is blank or unrecognised

    @property
    def discount_amount(self) -> Decimal:
        return (self.price * self.discount_pct / 100).quantize(Decimal("0.01"))

    @property
    def net_price(self) -> Decimal:
        return self.price - self.discount_amount


@dataclass(frozen=True)
class SkippedRow:
    row: int
    ticket_id: str
    reason: str
    value: str


@dataclass
class LoadResult:
    bookings: list[Booking] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)

    @property
    def rows_read(self) -> int:
        return len(self.bookings) + len(self.skipped)


def _normalise_header(value: object) -> str:
    return " ".join(str(value).split()).lower() if value is not None else ""


def map_headers(header_row: tuple[object, ...]) -> dict[str, int]:
    """Return {field name: column index}; raise WorkbookError if a required column is missing."""
    found = {_normalise_header(cell): i for i, cell in enumerate(header_row)}
    mapping: dict[str, int] = {}
    for name, spellings in COLUMNS.items():
        for spelling in spellings:
            if spelling in found:
                mapping[name] = found[spelling]
                break
    missing = [COLUMNS[name][0] for name in REQUIRED if name not in mapping]
    if missing:
        raise WorkbookError(
            "Missing required column(s): " + ", ".join(missing) + ". Check the first row of the sheet."
        )
    return mapping


def parse_money(value: object) -> Decimal:
    """Parse 12.5, "12.50", "$1,200.00". Raise ValueError on anything else."""
    if isinstance(value, bool) or value is None:
        raise ValueError
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError
    return amount.quantize(Decimal("0.01"))


def parse_discount(value: object) -> Decimal:
    """Parse a discount percentage from 0 to 100; a blank cell means no discount."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return Decimal("0")
    if isinstance(value, bool):
        raise ValueError
    text = str(value).strip().rstrip("%").strip()
    try:
        pct = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError from exc
    if not pct.is_finite() or not 0 <= pct <= 100:
        raise ValueError
    return pct


def parse_loyalty(value: object) -> bool | None:
    text = str(value).strip().lower() if value is not None else ""
    if text in YES:
        return True
    if text in NO:
        return False
    return None


def parse_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return dt.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def parse_row(row_number: int, values: tuple[object, ...], mapping: dict[str, int]) -> Booking | SkippedRow:
    def cell(name: str) -> object:
        index = mapping.get(name)
        if index is None or index >= len(values):
            return None
        return values[index]

    ticket_id = _text(cell("ticket_id"))

    def skip(reason: str, value: object) -> SkippedRow:
        shown = "(blank)" if _text(value) == "" else repr(value) if isinstance(value, str) else str(value)
        return SkippedRow(row_number, ticket_id, reason, shown)

    for name, label in (
        ("ticket_id", "TicketID"),
        ("passenger", "PassengerName"),
        ("route", "Route"),
        ("ticket_class", "Class"),
    ):
        if _text(cell(name)) == "":
            return skip(f"{label} is empty", cell(name))

    raw_status = cell("status")
    status_text = _text(raw_status).lower()
    if status_text == "":
        return skip("Status is empty", raw_status)
    if status_text not in STATUSES:
        return skip("Unknown status", raw_status)

    try:
        price = parse_money(cell("price"))
    except ValueError:
        return skip("Price is not a number", cell("price"))

    try:
        discount = parse_discount(cell("discount"))
    except ValueError:
        return skip("Discount is not a percentage from 0 to 100", cell("discount"))

    return Booking(
        row=row_number,
        ticket_id=ticket_id,
        passenger=_text(cell("passenger")),
        route=_text(cell("route")),
        ticket_class=_text(cell("ticket_class")),
        price=price,
        status=STATUSES[status_text],
        date=parse_date(cell("date")),
        discount_pct=discount,
        loyalty=parse_loyalty(cell("loyalty")),
    )


def load_bookings(path: str | Path) -> LoadResult:
    """Load the active sheet of an .xlsx file. Bad rows are collected, not fatal."""
    path = Path(path)
    if not path.is_file():
        raise WorkbookError(f"File not found: {path}")
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise WorkbookError(f"Could not open {path} as an Excel .xlsx workbook ({exc}).") from exc

    try:
        rows = workbook.active.iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            raise WorkbookError(f"{path} is empty.")
        mapping = map_headers(header)

        result = LoadResult()
        for row_number, values in enumerate(rows, start=2):
            if all(_text(v) == "" for v in values):
                continue  # fully blank row
            parsed = parse_row(row_number, values, mapping)
            if isinstance(parsed, Booking):
                result.bookings.append(parsed)
            else:
                result.skipped.append(parsed)
        return result
    finally:
        workbook.close()
