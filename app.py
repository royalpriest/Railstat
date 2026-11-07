"""Web front end: upload a bookings workbook, get the HTML dashboard back.

Runs locally with `flask --app app run` and on Vercel as a Python function.
Uploaded files are processed in memory/temp storage and never kept.
"""

from __future__ import annotations

import datetime as dt
import functools
import hashlib
import io
import tempfile
from pathlib import Path

from flask import Flask, Response, render_template, request, send_file
from openpyxl import Workbook
from werkzeug.exceptions import RequestEntityTooLarge

from report_tool.charts import weekly_revenue
from report_tool.html_report import render_html
from report_tool.loader import (
    LoadResult,
    MissingColumnsError,
    NotAWorkbookError,
    WorkbookError,
    load_bookings,
)
from report_tool.summary import summarize

SAMPLE = Path(__file__).parent / "samples" / "bookings_sample.xlsx"
MAX_UPLOAD_MB = 4  # Vercel functions accept request bodies up to 4.5 MB

# (header, required, example) shown on the landing page and used for the template download.
COLUMNS = [
    ("TicketID", True, "TB-1042"),
    ("PassengerName", True, "Maria Gonzalez"),
    ("Route", True, "Toronto–Montréal"),
    ("Class", True, "Economy"),
    ("Price", True, "85.50 or $85.50"),
    ("Status", True, "Confirmed / Cancelled"),
    ("Date", False, "2026-09-08"),
    ("DiscountApplied", False, "10 or 10%"),
    ("LoyaltyMember", False, "Yes / No"),
]
TEMPLATE_ROWS = [
    [
        "TB-1042",
        "Maria Gonzalez",
        "Toronto–Montréal",
        "Economy",
        85.5,
        "Confirmed",
        dt.date(2026, 9, 8),
        10,
        "Yes",
    ],
    [
        "TB-1043",
        "Sam Patel",
        "Ottawa–Québec City",
        "Business",
        142,
        "Cancelled",
        dt.date(2026, 9, 9),
        0,
        "No",
    ],
]

app = Flask(__name__, template_folder="report_tool/templates")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


@functools.cache
def sample_preview() -> dict:
    """Figures from the sample workbook for the small dashboard preview on the landing page."""
    summary = summarize(load_bookings(SAMPLE).bookings)
    top = summary.routes_by_volume()[:3]
    widest = max((counts.total for _, counts in top), default=1)
    routes = [
        {
            "name": name,
            "confirmed_pct": round(100 * counts.confirmed / widest, 1),
            "cancelled_pct": round(100 * counts.cancelled / widest, 1),
            "cancelled": counts.cancelled,
        }
        for name, counts in top
    ]
    series = weekly_revenue(summary.confirmed)
    spark = ""
    if len(series) > 1:
        peak = float(max(value for _, value in series)) or 1
        step = 300 / (len(series) - 1)
        spark = " ".join(
            f"{round(i * step, 1)},{round(64 - 58 * float(value) / peak, 1)}"
            for i, (_, value) in enumerate(series)
        )
    return {
        "source": SAMPLE.name,
        "revenue": f"${summary.net_revenue:,.2f}",
        "cancel_rate": f"{summary.cancellation_rate:.1%}",
        "routes": routes,
        "spark": spark,
    }


def landing_page(error: dict | None = None, status: int = 200) -> tuple[str, int]:
    page = render_template(
        "landing.html",
        error=error,
        max_mb=MAX_UPLOAD_MB,
        preview=sample_preview(),
        columns=COLUMNS,
    )
    return page, status


def problem(title: str, text: str, template_link: bool = False) -> dict:
    return {"title": title, "text": text, "template_link": template_link}


def explain(exc: WorkbookError, name: str) -> dict:
    """Turn a loader error into a message that says what's wrong and how to fix it."""
    if isinstance(exc, NotAWorkbookError):
        return problem(
            f"{name} isn't a readable Excel file.",
            "Open it in Excel and choose Save As › Excel Workbook (.xlsx), then upload it again.",
        )
    if isinstance(exc, MissingColumnsError):
        plural = "s" if len(exc.missing) > 1 else ""
        return problem(
            f"{name} is missing the {', '.join(exc.missing)} column{plural}.",
            f"Its first row has: {', '.join(exc.found) or 'nothing'}. "
            "Add the missing header, or start from the template.",
            template_link=True,
        )
    return problem(f"{name} couldn't be read.", str(exc))


def report_response(result: LoadResult, source: str, data: bytes, show_names: bool) -> Response:
    html = render_html(
        summarize(result.bookings),
        result.skipped,
        source=source,
        source_sha256=hashlib.sha256(data).hexdigest(),
        generated_at=dt.datetime.now(dt.UTC).replace(tzinfo=None),
        show_names=show_names,
    )
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    return response


def build_report(data: bytes, source: str, show_names: bool) -> Response | tuple[str, int]:
    # openpyxl needs a real file; the temp file is deleted as soon as it's read.
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as handle:
        handle.write(data)
        handle.flush()
        try:
            result = load_bookings(handle.name)
        except WorkbookError as exc:
            exc.args = (str(exc).replace(handle.name, source),)
            return landing_page(explain(exc, source), 400)
    if not result.bookings:
        return landing_page(
            problem(
                f"None of the rows in {source} could be used.",
                "Check that Price is a number and Status is Confirmed or Cancelled.",
                template_link=True,
            ),
            400,
        )
    return report_response(result, source, data, show_names)


@app.get("/")
def index():
    return landing_page()


@app.post("/report")
def report():
    upload = request.files.get("workbook")
    if upload is None or not upload.filename:
        return landing_page(problem("No file chosen.", "Choose an .xlsx file to upload."), 400)
    name = Path(upload.filename).name
    if not name.lower().endswith(".xlsx"):
        return landing_page(
            problem(
                f"{name} isn't an .xlsx file.",
                "Only Excel .xlsx files are supported. In Excel, choose Save As › Excel Workbook (.xlsx).",
            ),
            400,
        )
    return build_report(upload.read(), name, show_names=request.form.get("show_names") == "on")


@app.get("/sample")
def sample():
    data = SAMPLE.read_bytes()
    return report_response(load_bookings(SAMPLE), SAMPLE.name, data, show_names=False)


@app.get("/template.xlsx")
def template():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Bookings"
    sheet.append([name for name, _, _ in COLUMNS])
    for row in TEMPLATE_ROWS:
        sheet.append(row)
    for cell in sheet["G"][1:]:
        cell.number_format = "yyyy-mm-dd"
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="railstat_template.xlsx",
    )


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return landing_page(
        problem(
            f"That file is larger than {MAX_UPLOAD_MB} MB.",
            "Remove unused sheets or rows and try again.",
        ),
        413,
    )
