import io
from pathlib import Path

import pytest

from app import app

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
    assert "A. L••" in response.get_data(as_text=True)
    assert b"Ann Lee" not in response.data
    assert b"Ann Lee" in upload(client, data, show_names="on").data


def test_rejects_missing_wrong_type_and_bad_files(client, make_workbook):
    assert client.post("/report", data={}).status_code == 400
    assert b"Only Excel .xlsx" in upload(client, b"a,b", name="bookings.csv").data
    response = upload(client, b"not a workbook")
    assert response.status_code == 400
    assert b"Could not open bookings.xlsx" in response.data
    assert b"/tmp" not in response.data  # temp paths aren't leaked
    no_rows = make_workbook(
        [["TB-1", "Ann", "A-B", "Economy", "TBD", "Confirmed", None, 0, "No"]]
    ).read_bytes()
    assert b"No valid bookings" in upload(client, no_rows).data


def test_too_large(client, monkeypatch):
    monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 10)
    response = upload(client, b"x" * 100)
    assert response.status_code == 413
