"""Web front end: upload a bookings workbook, get the HTML dashboard back.

Runs locally with `flask --app app run` and on Vercel as a Python function.
Uploaded files are processed in memory/temp storage and never kept.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import tempfile
from pathlib import Path

from flask import Flask, Response, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from report_tool.html_report import render_html
from report_tool.loader import LoadResult, WorkbookError, load_bookings
from report_tool.summary import summarize

SAMPLE = Path(__file__).parent / "samples" / "bookings_sample.xlsx"
MAX_UPLOAD_MB = 4  # Vercel functions accept request bodies up to 4.5 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def upload_page(error: str | None = None, status: int = 200) -> tuple[str, int]:
    return render_template("upload.html", error=error, max_mb=MAX_UPLOAD_MB), status


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
            message = str(exc).replace(handle.name, source)
            return upload_page(message, 400)
    if not result.bookings:
        return upload_page(f"No valid bookings found in {source}. Check the columns and try again.", 400)
    return report_response(result, source, data, show_names)


@app.get("/")
def index():
    return upload_page()


@app.post("/report")
def report():
    upload = request.files.get("workbook")
    if upload is None or not upload.filename:
        return upload_page("Choose an .xlsx file to upload.", 400)
    name = Path(upload.filename).name
    if not name.lower().endswith(".xlsx"):
        return upload_page("Only Excel .xlsx files are supported.", 400)
    return build_report(upload.read(), name, show_names=request.form.get("show_names") == "on")


@app.get("/sample")
def sample():
    data = SAMPLE.read_bytes()
    return report_response(load_bookings(SAMPLE), SAMPLE.name, data, show_names=False)


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return upload_page(f"That file is larger than {MAX_UPLOAD_MB} MB.", 413)
