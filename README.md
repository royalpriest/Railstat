<img src="assets/railstat-mark.svg" width="56" height="56" alt="Railstat logo">

# Railstat: Data Analysis & Automated Reporting Tool

### Project Overview
Railstat is a Python package and a Flask web app. Together they turn a raw bookings spreadsheet into a validated, interactive dashboard. You can use it from the command line (`report-tool bookings.xlsx`), or upload a workbook in the browser and get the dashboard back.

It started as a single Jupyter notebook (`Project.ipynb`, kept for reference). I rebuilt it as a tested, packaged application to show how I take a working script to production quality on both the back end and the front end.

### What it demonstrates
**Back end (Python)**
- **Package design:** the code is split into modules with a single job each: loading and validation (`loader.py`), aggregation (`summary.py`), rendering (`html_report.py`, `render.py`) and privacy (`privacy.py`). The `report-tool` console script is installed through `pyproject.toml`.
- **Defensive input handling:** every row is validated on its own. Malformed values such as a blank status, a price like "TBD" or an unknown status are set aside with a reason instead of crashing the run. Bad files and missing columns raise typed exceptions that map to clear messages and exit codes.
- **Correctness:** money is handled with `Decimal` and rounded to cents. Columns are matched by header name, not position.
- **Testing and CI:** 53 pytest tests build their workbooks inside each test, and cover the loader, the summary math, the CLI, the HTML output and the web app. GitHub Actions runs ruff lint and format checks plus the test suite on Python 3.11, 3.12 and 3.13.

**Full stack (web)**
- **Flask app (`app.py`):** routes for the landing page, upload (`POST /report`), a sample report and a downloadable template workbook. Uploads are capped at 4 MB, kept in temporary files that are deleted right after parsing, and served with `Cache-Control: no-store`.
- **Front end:** Jinja2 templates with a drag-and-drop upload and client-side checks of file type and size. The dashboard is a single self-contained HTML file. It recomputes its filters, period comparisons, charts and the sortable, paged table in vanilla JavaScript, with no charting library.
- **UX and accessibility:** light and dark themes that remember your choice, a responsive layout that works on phones, `aria-sort` on sortable headers, and charts that don't rely on colour alone.
- **Security and privacy:** Jinja2 autoescaping stops spreadsheet text from injecting HTML. CSV cells that could run as spreadsheet formulas are neutralised. Passenger names are masked unless you opt in.
- **Deployment:** it deploys to Vercel's Python runtime with no extra configuration.

### Features
- **Automated ingestion:** reads the active sheet of an `.xlsx` workbook with openpyxl, matching columns by header name, so the column order doesn't matter.
- **Row-level validation:** bad rows are skipped and listed with their Excel row number, ticket ID and reason.
- **Exact money math:** prices, discounts and revenue use `Decimal`, rounded to cents.
- **HTML dashboard report (default):** one self-contained file such as `reports/booking_summary_20261031_140211.html` that opens in any browser. It contains:
  - filters for period (all weeks, or the last few weeks), route and class;
  - headline numbers (net revenue, confirmed tickets, cancellation rate, loyalty share), each showing its change against the previous period;
  - a line saying whether every row was used;
  - weekly net revenue, with the compared weeks shaded and the high and low weeks labelled;
  - cancellation rate by route, measured against the average;
  - bookings by route and by class;
  - a bookings table you can sort, search and page through.

  It has Export CSV and Print / Save PDF buttons and a light/dark switch, uses DM Sans for the interface and Space Mono for compact data labels (with offline system fallbacks), and works on a phone.
- **Text report:** `--format txt` (or `both`) writes the same figures as plain text.
- **Skipped rows:** listed in the report and saved next to it as `..._skipped_rows.csv`.
- **Privacy by default:** passenger names are masked (`Maria Gonzalez` becomes `M. G•••••••`) and full names are never written to the file unless you pass `--show-names`. Spreadsheet text is HTML-escaped, and CSV cells that could run as spreadsheet formulas are neutralised.
- **Cross-platform:** `--open` opens the report with the default app on Windows, macOS or Linux.

### Expected columns
`TicketID`, `PassengerName`, `Route`, `Class`, `Price`, `Status` are required. `Date`, `DiscountApplied` (a percentage from 0 to 100; blank means none) and `LoyaltyMember` (Yes/No) are optional. Header names are matched without regard to case or spacing.

### Technical Stack
**Back end:** Python 3.11+, openpyxl, Flask, Jinja2  
**Front end:** HTML, CSS, vanilla JavaScript, inline SVG charts  
**Tooling:** pytest, ruff, GitHub Actions CI, Vercel

### Project Structure
```
app.py                  Flask web app (upload page, report, sample, template)
report_tool/
  loader.py             read the workbook and validate each row
  summary.py            aggregate bookings into report figures
  html_report.py        render the self-contained HTML dashboard
  render.py             plain-text report
  privacy.py            name masking
  cli.py                report-tool command
  templates/            Jinja2 templates for the landing page and dashboard
tests/                  pytest suite
samples/                sample workbook and its generator
```

### How to Use
```bash
pip install .
report-tool samples/bookings_sample.xlsx            # HTML report in ./reports/
report-tool bookings.xlsx --out my_reports --open   # choose a folder and open the report
report-tool bookings.xlsx --format both             # HTML and text
report-tool bookings.xlsx --show-names              # include full passenger names
report-tool                                          # asks for the file path
```
You can also run it without installing: `python -m report_tool bookings.xlsx`. Use `-v` to log each skipped row in the terminal.

Exit codes: `0` report written, `1` no valid bookings found, `2` the file couldn't be read or is missing required columns.

### Development
```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
python samples/make_sample.py   # regenerate the sample workbook
```

`Project.ipynb` is the original notebook version, kept for reference. The maintained code is in `report_tool/`.

### Web app (Vercel)
`app.py` is a small Flask app. The landing page explains the tool, shows a preview built from the sample file, and takes an `.xlsx` upload (up to 4 MB, drag and drop or browse) that returns the HTML dashboard. `/sample` shows the sample report and `/template.xlsx` downloads a blank workbook with the right headers. Upload problems (wrong file type, missing columns, no usable rows) are explained in plain words with how to fix them. The page uses a light retro design with warm paper surfaces, muted modular accents and DM Sans typography and has a light/dark switch that remembers your choice. Uploads are processed in a temporary file that is deleted straight away; nothing is stored. Passenger names stay masked unless the "Show full passenger names" box is ticked.

```bash
flask --app app run          # http://127.0.0.1:5000
```

On Vercel it deploys with no extra configuration: Vercel finds `app.py` and installs the dependencies from `pyproject.toml`.

