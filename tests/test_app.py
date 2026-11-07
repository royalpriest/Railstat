import io
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app import app
from tests.conftest import HEADER

SAMPLE = Path(__file__).parent.parent / "samples" / "bookings_sample.xlsx"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def upload(client, data: bytes, name: str = "bookings.xlsx", **form):
    return client.post(
        "/report",
        data={"workbook": (io.BytesIO(data), name), **form},
        content_type="multipart/form-data",
    )


def test_upload_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'name="workbook"' in response.data
    assert b"Space Mono" in response.data
    assert b'id="theme-toggle"' in response.data
    assert b"TicketID" in response.data and b"LoyaltyMember" in response.data
    assert b'id="error" role="alert" hidden' in response.data


def test_template_download(client):
    response = client.get("/template.xlsx")
    assert response.status_code == 200
    assert "railstat_template.xlsx" in response.headers["Content-Disposition"]
    sheet = load_workbook(io.BytesIO(response.data)).active
    assert [c.value for c in sheet[1]][:6] == [
        "TicketID",
        "PassengerName",
        "Route",
        "Class",
        "Price",
        "Status",
    ]
    assert sheet.max_row == 3


def test_sample_report(client):
    response = client.get("/sample")
    assert response.status_code == 200
    assert b"Train bookings report" in response.data
    assert b"3 rows were skipped" in response.data


def test_upload_builds_report_with_names_masked(client, make_workbook):
    data = make_workbook(
        [["TB-1", "Ann Lee", "A-B", "Economy", 10, "Confirmed", None, 0, "Yes"]]
    ).read_bytes()
    response = upload(client, data)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert r"A. L\u2022\u2022" in response.get_data(as_text=True)
    assert b"Ann Lee" not in response.data
    assert b"Ann Lee" in upload(client, data, show_names="on").data


def test_rejects_missing_wrong_type_and_bad_files(client, make_workbook):
    assert client.post("/report", data={}).status_code == 400
    assert b"bookings.csv isn&#39;t an .xlsx file" in upload(client, b"a,b", name="bookings.csv").data
    response = upload(client, b"not a workbook")
    assert response.status_code == 400
    assert b"bookings.xlsx isn&#39;t a readable Excel file" in response.data
    assert b"/tmp" not in response.data  # temp paths aren't leaked
    no_rows = make_workbook(
        [["TB-1", "Ann", "A-B", "Economy", "TBD", "Confirmed", None, 0, "No"]]
    ).read_bytes()
    assert b"None of the rows in bookings.xlsx could be used" in upload(client, no_rows).data


def test_missing_column_message_links_template(client, make_workbook):
    path = make_workbook([["TB-1", "Ann", "A-B", "Economy", 10]], header=HEADER[:5])
    response = upload(client, path.read_bytes())
    text = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "missing the Status column" in text
    assert 'href="/template.xlsx">Download the template' in text


def test_too_large(client, monkeypatch):
    monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 10)
    response = upload(client, b"x" * 100)
    assert response.status_code == 413
    assert b"larger than" in response.data
