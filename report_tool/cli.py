"""Command-line entry point: report-tool bookings.xlsx"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys
from pathlib import Path

from report_tool import __version__
from report_tool.loader import WorkbookError, load_bookings
from report_tool.render import render_text
from report_tool.summary import summarize

log = logging.getLogger("report_tool")

EXIT_OK = 0
EXIT_NO_BOOKINGS = 1
EXIT_BAD_INPUT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="report-tool",
        description="Summarise a train bookings Excel workbook into a text report.",
    )
    parser.add_argument("workbook", nargs="?", help="path to the .xlsx file (asked for if left out)")
    parser.add_argument("-o", "--out", default="reports", help="folder for the report (default: reports)")
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
    report = render_text(summary, result.skipped, source=Path(workbook).name, generated_at=now)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"booking_summary_{now:%Y%m%d_%H%M%S}.txt"
    out_path.write_text(report, encoding="utf-8")
    log.info("Report saved to %s", out_path)

    if args.open:
        open_file(out_path)
    return EXIT_OK
