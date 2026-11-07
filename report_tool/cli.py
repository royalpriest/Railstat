"""Command-line entry point: report-tool bookings.xlsx"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

from report_tool import __version__
from report_tool.html_report import render_html
from report_tool.loader import SkippedRow, WorkbookError, load_bookings
from report_tool.render import render_text
from report_tool.summary import summarize

log = logging.getLogger("report_tool")

EXIT_OK = 0
EXIT_NO_BOOKINGS = 1
EXIT_BAD_INPUT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="report-tool",
        description="Summarise a train bookings Excel workbook into an HTML dashboard or text report.",
    )
    parser.add_argument("workbook", nargs="?", help="path to the .xlsx file (asked for if left out)")
    parser.add_argument("-o", "--out", default="reports", help="folder for the report (default: reports)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["html", "txt", "both"],
        default="html",
        help="report format (default: html)",
    )
    parser.add_argument(
        "--show-names", action="store_true", help="include full passenger names (masked by default)"
    )
    parser.add_argument("--open", action="store_true", help="open the report when it's written")
    parser.add_argument("-v", "--verbose", action="store_true", help="log each skipped row")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def open_file(path: Path) -> None:
    """Open a file with the system's default app on Windows, macOS or Linux."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        log.warning("Could not open %s: %s", path, exc)


def main(argv: list[str] | None = None, now: dt.datetime | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    workbook = args.workbook or input("Path to the train bookings .xlsx file: ").strip().strip('"')
    try:
        result = load_bookings(workbook)
    except WorkbookError as exc:
        log.error("Error: %s", exc)
        return EXIT_BAD_INPUT

    for item in result.skipped:
        log.debug("Skipped row %s: %s (%s)", item.row, item.reason, item.value)
    if result.skipped:
        log.warning("%d row(s) skipped; details are in the report.", len(result.skipped))
    if not result.bookings:
        log.error("No valid bookings found in %s.", workbook)
        return EXIT_NO_BOOKINGS

    now = now or dt.datetime.now()
    summary = summarize(result.bookings)
    source = Path(workbook).name
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"booking_summary_{now:%Y%m%d_%H%M%S}"

    skipped_csv = None
    if result.skipped:
        skipped_csv = out_dir / f"{stem}_skipped_rows.csv"
        write_skipped_csv(skipped_csv, result.skipped)
        log.info("Skipped rows saved to %s", skipped_csv)

    written: list[Path] = []
    if args.format in ("txt", "both"):
        path = out_dir / f"{stem}.txt"
        text = render_text(
            summary, result.skipped, source=source, generated_at=now, show_names=args.show_names
        )
        path.write_text(text, encoding="utf-8")
        written.append(path)
    if args.format in ("html", "both"):
        path = out_dir / f"{stem}.html"
        html = render_html(
            summary,
            result.skipped,
            source=source,
            source_sha256=sha256_of(Path(workbook)),
            generated_at=now,
            show_names=args.show_names,
            skipped_csv_name=skipped_csv.name if skipped_csv else None,
        )
        path.write_text(html, encoding="utf-8")
        written.append(path)

    for path in written:
        log.info("Report saved to %s", path)
    if args.open:
        open_file(written[-1])
    return EXIT_OK


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_skipped_csv(path: Path, skipped: list[SkippedRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["excel_row", "ticket_id", "reason", "value_found"])
        for item in skipped:
            writer.writerow([item.row, _csv_safe(item.ticket_id), item.reason, _csv_safe(item.value)])


def _csv_safe(value: str) -> str:
    """Stop spreadsheet apps from running a cell copied from the input as a formula."""
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value
