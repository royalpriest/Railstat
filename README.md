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
- **Report generation:** writes a time-stamped report such as `reports/booking_summary_20261031_140211.txt` with net revenue, discounts, cancellation rate, average ticket, tickets by class, bookings by route (busiest first), every confirmed and cancelled booking, and the skipped rows.
- **Cross-platform:** `--open` opens the report with the default app on Windows, macOS or Linux.

### Expected columns
`TicketID`, `PassengerName`, `Route`, `Class`, `Price`, `Status` are required. `Date`, `DiscountApplied` (a percentage from 0 to 100; blank means none) and `LoyaltyMember` (Yes/No) are optional. Header names are matched without regard to case or spacing.

### Technical Stack
Python 3.11+, openpyxl, pytest and ruff for development, GitHub Actions for CI.

### How to Use
```bash
pip install .
report-tool samples/bookings_sample.xlsx           # writes to ./reports/
report-tool bookings.xlsx --out my_reports --open  # choose a folder and open the report
report-tool                                         # asks for the file path
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
