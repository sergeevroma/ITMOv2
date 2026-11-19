import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi.testclient import TestClient

from roombook.main import create_app

from .conftest import DAY


def test_simultaneous_requests_cannot_double_book(database_path, booking):
    barrier = Barrier(8)
    with TestClient(create_app(database_path)) as client:

        def submit(_index):
            barrier.wait(timeout=10)
            return client.post("/api/bookings", json=booking).status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(submit, range(8)))
        assert sorted(statuses) == [201] + [409] * 7
        assert len(client.get("/api/bookings", params={"date": DAY}).json()) == 1


def test_factory_and_schema_export_do_not_create_database(tmp_path):
    path = tmp_path / "data" / "test.sqlite3"
    application = create_app(path)
    assert application.openapi()["info"]["title"] == "RoomBook"
    assert not path.parent.exists()


def test_static_frontend_and_api_can_share_origin(tmp_path, database_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<h1>Test page</h1>", encoding="utf-8")
    with TestClient(create_app(database_path, frontend)) as client:
        assert client.get("/").text == "<h1>Test page</h1>"
        assert client.get("/api/rooms").status_code == 200
        assert client.get("/openapi.json").json()["info"]["title"] == "RoomBook"


def test_exported_openapi_matches_application(client):
    path = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    assert client.get("/openapi.json").json() == json.loads(path.read_text(encoding="utf-8"))
    assert client.get("/docs").status_code == 200


def test_malformed_json_has_a_form_error(client):
    response = client.post(
        "/api/bookings", content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"]
    assert response.json()["error"]["fields"]["_form"]


def test_unknown_room_filter_has_a_field_error(client):
    response = client.get("/api/bookings", params={"date": DAY, "room_id": 999})
    assert response.status_code == 422
    assert response.json()["error"]["fields"]["room_id"]
