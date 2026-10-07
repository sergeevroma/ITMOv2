import importlib.util
import io
import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

from app.api import create_app

SKILL_DIR = (
    Path(__file__).resolve().parents[2]
    / ".opencode" / "skills" / "booking-csv-audit"
)
EXAMPLES = SKILL_DIR / "examples"


@pytest.fixture
def audit():
    spec = importlib.util.spec_from_file_location(
        "booking_csv_audit", SKILL_DIR / "scripts" / "audit_csv.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def api(tmp_path, audit, monkeypatch):
    with TestClient(create_app(tmp_path / "audit.sqlite3")) as client:
        payload = json.loads((EXAMPLES / "schedule.json").read_text())
        assert client.post("/bookings", json=payload).status_code == 201

        def open_request(request, timeout):
            assert request.get_method() == "GET"
            assert timeout > 0
            url = urlsplit(request.full_url)
            response = client.get(url.path + "?" + url.query)
            assert response.status_code == 200
            stream = io.BytesIO(response.content)
            stream.status = 200
            return stream

        monkeypatch.setattr(audit, "urlopen", open_request)
        yield client


@pytest.mark.parametrize("name", ["clean", "issues", "schedule-conflict"])
def test_examples_match_known_results_and_leave_schedule_unchanged(audit, api, name):
    before = api.get("/bookings", params={"date": "2099-10-12"}).json()
    report = audit.audit_csv(EXAMPLES / f"{name}.csv", "http://demo")
    expected = json.loads((EXAMPLES / "expected.json").read_text())[name]
    assert report["status"] == expected["status"]
    assert report["summary"] == expected["summary"]
    assert [row["row"] for row in report["invalid_rows"]] == expected["invalid_rows"]
    assert report["conflicts"] == expected["conflicts"]
    assert report["errors"] == []
    assert api.get("/bookings", params={"date": "2099-10-12"}).json() == before


def test_unavailable_api_is_a_failed_audit(audit, monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("API unavailable")

    monkeypatch.setattr(audit, "urlopen", unavailable)
    report = audit.audit_csv(EXAMPLES / "clean.csv", "http://offline")
    assert report["status"] == "failed"
    assert "API unavailable" in report["errors"][0]


@pytest.mark.parametrize("content", [b"not JSON", b'{}', b'[{"id": 1}]'])
def test_invalid_api_response_is_not_treated_as_empty(audit, monkeypatch, content):
    def invalid_response(*args, **kwargs):
        stream = io.BytesIO(content)
        stream.status = 200
        return stream

    monkeypatch.setattr(audit, "urlopen", invalid_response)
    report = audit.audit_csv(EXAMPLES / "clean.csv", "http://invalid")
    assert report["status"] == "failed"
    assert report["errors"]


@pytest.mark.parametrize(
    "header", ["room_id,title", "room_id,title,date,start,end,extra"]
)
def test_invalid_header_is_reported(audit, tmp_path, header):
    source = tmp_path / "bad.csv"
    source.write_text(header + "\n", encoding="utf-8")
    report = audit.audit_csv(source, "http://unused")
    assert report["status"] == "failed"
    assert "колонки" in report["errors"][0]


def test_cli_writes_both_reports_with_meaningful_exit_status(audit, api, tmp_path):
    code = audit.main([
        "--csv", str(EXAMPLES / "issues.csv"),
        "--api-url", "http://demo", "--output-dir", str(tmp_path),
    ])
    assert code == 1
    report = json.loads((tmp_path / "issues.json").read_text())
    markdown = (tmp_path / "issues.md").read_text()
    assert report["status"] == "issues_found"
    assert "| 2 | csv | запись 3 |" in markdown
    assert "| 3 | csv | запись 2 |" in markdown
    assert "| 4 |" in markdown and "| 5 |" in markdown
