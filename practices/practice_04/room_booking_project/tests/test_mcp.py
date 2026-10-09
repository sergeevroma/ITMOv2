import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
import pytest

DAY = "2099-10-12"
PRACTICE_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def server():
    spec = importlib.util.spec_from_file_location(
        "roombook_mcp", PRACTICE_DIR / "mcp" / "server.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def api(tmp_path, server, monkeypatch):
    from app.api import create_app

    with TestClient(create_app(tmp_path / "mcp.sqlite3")) as client:
        fixture = json.loads((
            PRACTICE_DIR / "demo" / "schedule.json"
        ).read_text())
        assert client.post("/bookings", json=fixture).status_code == 201

        def open_request(request, timeout):
            assert request.get_method() == "GET"
            assert timeout == 5
            url = urlsplit(request.full_url)
            response = client.get(url.path + "?" + url.query)
            stream = io.BytesIO(response.content)
            if response.status_code >= 400:
                raise HTTPError(
                    request.full_url, response.status_code, "API error", {}, stream,
                )
            return stream

        monkeypatch.setattr(server, "urlopen", open_request)
        yield client


@pytest.mark.parametrize("room_id, count", [(103, 14), (None, 48)])
def test_mcp_matches_api_and_does_not_change_bookings(server, api, room_id, count):
    before = api.get("/bookings", params={"date": DAY}).json()
    params = {"date": DAY, "duration_minutes": 60}
    if room_id is not None:
        params["room_id"] = room_id
    report = server.find_free_slots(**params)
    assert report["slots"] == api.get("/free-slots", params=params).json()
    assert report["count"] == count
    assert api.get("/bookings", params={"date": DAY}).json() == before


@pytest.mark.parametrize("changes", [
    {"duration_minutes": 0}, {"date": "wrong"}, {"room_id": 999},
])
def test_mcp_explains_invalid_input(server, api, changes):
    with pytest.raises(ValueError, match="HTTP 422"):
        server.find_free_slots(**{
            "date": DAY, "duration_minutes": 60, "room_id": 103, **changes,
        })


def test_mcp_reports_unavailable_api(server, monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(server, "urlopen", unavailable)
    with pytest.raises(ValueError, match="API RoomBook недоступен"):
        server.find_free_slots(DAY, 60)


@pytest.mark.parametrize("content", [b"not JSON", b"{}"])
def test_mcp_rejects_broken_api_response(server, monkeypatch, content):
    monkeypatch.setattr(server, "urlopen", lambda *args, **kw: io.BytesIO(content))
    with pytest.raises(ValueError, match="некорректный"):
        server.find_free_slots(DAY, 60)
