# Train-Booking-Data-Automated-Summarizer
# Data-Analysis & Automated Reporting Tool

### Project Overview
This project is a Python-based automation tool designed to ingest, normalize, and analyze complex datasets from Excel. While currently configured for financial/booking data, the core engine demonstrates the logic required for Security Log Parsing and Incident Reporting.

As a SOC Analyst candidate, I developed this to showcase my ability to handle data integrity, automate repetitive administrative tasks, and generate structured technical reports.

### Cybersecurity Relevance (SOC Context)
In a Security Operations Center (SOC), analysts must often parse through massive amounts of exported CSV/Excel data from SIEMs or Firewalls. This script demonstrates three critical SOC competencies:

Data Normalization: The script utilizes .strip().lower() and type-casting to ensure that inconsistent data inputs (e.g., "Confirmed " vs "confirmed") are normalized for accurate analysis.

Defensive Programming: Implements robust try-except blocks and pyinputplus validation to handle malformed files and user input errors, ensuring the tool doesn't crash during critical operations.

Automated Triage & Reporting: The script automatically categorizes records (Confirmed vs. Cancelled) and calculates metrics, mimicking the logic used to triage "True Positives" vs. "False Positives" in an alert queue.

### Features
Automated Ingestion: Uses openpyxl to parse multi-column Excel workbooks.

Input Validation: Uses pyinputplus to ensure file paths exist before execution.

Error Handling: Features granular exception handling for FileNotFound and general data corruption.

Report Generation: Automatically generates a time-stamped bookingSummary.txt and triggers a system process to open the report for immediate review.

### Technical Stack
Language: Python 3.12

Libraries: openpyxl (Excel handling), subprocess (System integration), datetime (Timestamping), pyinputplus (Secure input validation).

### Sample Output
The tool generates a structured report including:

Total Revenue and Discount Metrics (Financial Integrity)

Frequency analysis of routes and classes.

Full audit logs of confirmed and cancelled transactions.

### How to Use
Ensure Python 3.x is installed.

Install dependencies: pip install openpyxl pyinputplus.

Run the script: python main.py.

Enter the path to your .xlsx data file when prompted.
