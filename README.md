# Data Analysis & Automated Reporting Tool

### Project Overview
This project is a Python-based automation tool designed to ingest, normalize, and analyze complex datasets from Excel. While currently configured for financial/booking data, the core engine demonstrates the logic required for Security Log Parsing and Incident Reporting.

As a SOC Analyst candidate, I developed this to showcase my ability to handle data integrity, automate repetitive administrative tasks, and generate structured technical reports.

### Cybersecurity Relevance (SOC Context)
In a Security Operations Center (SOC), analysts must often parse through massive amounts of exported CSV/Excel data from SIEMs or Firewalls. This tool demonstrates three critical SOC competencies:

**Data Normalization:** Status, class, loyalty and money values are trimmed, case-normalized and type-checked (for example "Confirmed " and "confirmed" are treated the same, and "$1,200" is read as 1200.00), so inconsistent inputs are analyzed accurately.

**Defensive Programming:** Every row is validated on its own. A malformed row (blank status, a price like "TBD", an unknown status) is set aside with the reason instead of crashing the run, and unreadable files or missing columns stop with a clear message and a non-zero exit code.

**Automated Triage & Reporting:** Records are categorized (Confirmed vs. Cancelled) and metrics calculated, mimicking the logic used to triage "True Positives" vs. "False Positives" in an alert queue. Rows that couldn't be processed are listed in the report so nothing disappears silently.

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

  It has Export CSV and Print / Save PDF buttons and a light/dark switch, uses the Space Mono font (falling back to the system monospace font offline), and works on a phone.
- **Text report:** `--format txt` (or `both`) writes the same figures as plain text.
- **Skipped rows:** listed in the report and saved next to it as `..._skipped_rows.csv`.
- **Privacy by default:** passenger names are masked (`Maria Gonzalez` becomes `M. G•••••••`) and full names are never written to the file unless you pass `--show-names`. Spreadsheet text is HTML-escaped, and CSV cells that could run as spreadsheet formulas are neutralised.
- **Cross-platform:** `--open` opens the report with the default app on Windows, macOS or Linux.

### Expected columns
`TicketID`, `PassengerName`, `Route`, `Class`, `Price`, `Status` are required. `Date`, `DiscountApplied` (a percentage from 0 to 100; blank means none) and `LoyaltyMember` (Yes/No) are optional. Header names are matched without regard to case or spacing.

### Technical Stack
Python 3.11+, openpyxl, Jinja2 (HTML report), pytest and ruff for development, GitHub Actions for CI.

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
`app.py` is a small Flask app. The landing page explains the tool, shows a preview built from the sample file, and takes an `.xlsx` upload (up to 4 MB, drag and drop or browse) that returns the HTML dashboard. `/sample` shows the sample report and `/template.xlsx` downloads a blank workbook with the right headers. Upload problems (wrong file type, missing columns, no usable rows) are explained in plain words with how to fix them. The page uses the Space Mono font and has a light/dark switch that remembers your choice. Uploads are processed in a temporary file that is deleted straight away; nothing is stored. Passenger names stay masked unless the "Show full passenger names" box is ticked.

```bash
flask --app app run          # http://127.0.0.1:5000
```

On Vercel it deploys with no extra configuration: Vercel finds `app.py` and installs the dependencies from `pyproject.toml`.
