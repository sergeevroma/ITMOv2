import pytest
from fastapi.testclient import TestClient

from roombook.main import create_app

from .conftest import DAY


def test_catalog_and_booking_rules(client):
    response = client.get("/api/rooms")
    assert response.status_code == 200
    assert [(room["id"], room["capacity"]) for room in response.json()] == [
        (101, 4),
        (102, 8),
        (103, 12),
    ]
    assert all(room["name"] and room["equipment"] for room in response.json())
    assert client.get("/api/booking-rules").json() == {
        "opens_at": "09:00",
        "closes_at": "18:00",
        "slot_minutes": 30,
        "timezone": "Europe/Moscow",
    }


def test_create_list_cancel_and_book_again(client, booking):
    assert client.get("/api/bookings", params={"date": DAY}).json() == []
    response = client.post("/api/bookings", json=booking)
    assert response.status_code == 201
    saved = response.json()
    assert saved == booking | {"id": saved["id"]}
    assert saved["id"] > 0
    assert client.get("/api/bookings", params={"date": DAY}).json() == [saved]
    response = client.delete(f"/api/bookings/{saved['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/bookings", params={"date": DAY}).json() == []
    assert client.post("/api/bookings", json=booking).status_code == 201


def test_trimmed_text_is_saved(client, booking):
    response = client.post(
        "/api/bookings", json=booking | {"title": "  Защита  ", "organizer": "  Роман  "}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Защита"
    assert response.json()["organizer"] == "Роман"


@pytest.mark.parametrize("start,end", [("09:00", "09:30"), ("17:30", "18:00"), ("09:00", "18:00")])
def test_workday_boundaries(client, booking, start, end):
    assert (
        client.post("/api/bookings", json=booking | {"start": start, "end": end}).status_code == 201
    )


@pytest.mark.parametrize(
    "start,end",
    [
        ("10:00", "11:00"),
        ("09:30", "10:30"),
        ("10:30", "11:30"),
        ("09:30", "11:30"),
        ("10:30", "11:00"),
    ],
)
def test_overlap_is_rejected_without_changing_schedule(client, booking, start, end):
    saved = client.post("/api/bookings", json=booking).json()
    response = client.post("/api/bookings", json=booking | {"start": start, "end": end})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "booking_conflict"
    assert response.json()["error"]["message"]
    assert client.get("/api/bookings", params={"date": DAY}).json() == [saved]


def test_adjacent_intervals_and_other_rooms_and_dates_are_allowed(client, booking):
    assert client.post("/api/bookings", json=booking).status_code == 201
    for change in [
        {"start": "09:00", "end": "10:00"},
        {"start": "11:00", "end": "12:00"},
        {"room_id": 102},
        {"date": "2027-03-16"},
    ]:
        assert client.post("/api/bookings", json=booking | change).status_code == 201


def test_filtering_and_stable_order(client, booking):
    payloads = [
        {"room_id": 102},
        {"start": "12:00", "end": "13:00"},
        {},
        {"date": "2027-03-16"},
    ]
    saved = [client.post("/api/bookings", json=booking | p).json() for p in payloads]
    assert client.get("/api/bookings", params={"date": DAY}).json() == [
        saved[2],
        saved[1],
        saved[0],
    ]
    assert client.get("/api/bookings", params={"date": DAY, "room_id": 102}).json() == [saved[0]]


@pytest.mark.parametrize(
    "change,field",
    [
        ({"title": "  "}, "title"),
        ({"organizer": ""}, "organizer"),
        ({"title": "a" * 121}, "title"),
        ({"organizer": "a" * 81}, "organizer"),
        ({"room_id": 999}, "room_id"),
        ({"room_id": True}, "room_id"),
        ({"room_id": "101"}, "room_id"),
        ({"date": "2027-02-30"}, "date"),
        ({"date": "20270315"}, "date"),
        ({"date": 0}, "date"),
        ({"start": "08:30"}, "start"),
        ({"end": "18:30"}, "end"),
        ({"start": "10:15"}, "start"),
        ({"end": "11:15"}, "end"),
        ({"end": "10:00"}, "end"),
        ({"end": "09:30"}, "end"),
        ({"start": "10:00:00"}, "start"),
        ({"start": "10:00+03:00"}, "start"),
        ({"end": "25:00"}, "end"),
        ({"organizer": 123}, "organizer"),
    ],
)
def test_invalid_fields_have_errors_and_do_not_save(client, booking, change, field):
    response = client.post("/api/bookings", json=booking | change)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"]
    assert error["fields"][field]
    assert client.get("/api/bookings", params={"date": DAY}).json() == []


@pytest.mark.parametrize("field", ["room_id", "title", "organizer", "date", "start", "end"])
def test_required_fields(client, booking, field):
    del booking[field]
    response = client.post("/api/bookings", json=booking)
    assert response.status_code == 422
    assert response.json()["error"]["fields"][field]


@pytest.mark.parametrize("params", [{}, {"date": "20270315"}, {"date": "2027-02-30"}])
def test_invalid_schedule_query(client, params):
    response = client.get("/api/bookings", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["fields"]["date"]


def test_missing_booking(client):
    response = client.delete("/api/bookings/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "booking_not_found"


def test_persistence_and_database_isolation(client, database_path, tmp_path, booking):
    saved = client.post("/api/bookings", json=booking).json()
    with TestClient(create_app(database_path)) as restarted:
        assert restarted.get("/api/bookings", params={"date": DAY}).json() == [saved]
    with TestClient(create_app(tmp_path / "other.sqlite3")) as other:
        assert other.get("/api/bookings", params={"date": DAY}).json() == []


def test_database_environment(monkeypatch, tmp_path, booking):
    path = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("ROOMBOOK_DB", str(path))
    with TestClient(create_app()) as client:
        assert client.post("/api/bookings", json=booking).status_code == 201
    assert path.is_file()
