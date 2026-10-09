from fastapi.testclient import TestClient
import pytest

from app.api import create_app

DAY = "2099-10-12"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "data" / "bookings.sqlite3"


@pytest.fixture
def client(db_path):
    with TestClient(create_app(db_path)) as session:
        yield session


def booking(**changes):
    base = {
        "room_id": 101,
        "title": "Подготовка к практике",
        "date": DAY,
        "start": "10:00",
        "end": "11:00",
    }
    return base | changes


def test_rooms(client):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 101, "name": "Комната 101"},
        {"id": 102, "name": "Комната 102"},
        {"id": 103, "name": "Комната 103"},
    ]


def test_create_and_read_booking(client):
    assert client.get("/bookings", params={"date": DAY}).json() == []
    response = client.post("/bookings", json=booking())
    assert response.status_code == 201
    saved = response.json()
    assert isinstance(saved["id"], int) and saved["id"] > 0
    assert saved == booking() | {"id": saved["id"]}
    listed = client.get("/bookings", params={"date": DAY})
    assert listed.status_code == 200
    assert listed.json() == [saved]


def test_title_is_trimmed(client):
    response = client.post("/bookings", json=booking(title="  Практика 4  "))
    assert response.status_code == 201
    assert response.json()["title"] == "Практика 4"
    assert (
        client.get("/bookings", params={"date": DAY}).json()[0]["title"]
        == "Практика 4"
    )


def test_persists_between_application_instances(client, db_path):
    response = client.post("/bookings", json=booking())
    assert response.status_code == 201
    saved = response.json()
    with TestClient(create_app(db_path)) as restarted:
        assert restarted.get("/bookings", params={"date": DAY}).json() == [saved]


def test_list_filters_date_and_sorts_by_room_and_start(client):
    payloads = [
        booking(room_id=102, start="09:00", end="09:30"),
        booking(start="11:00", end="12:00"),
        booking(start="09:30", end="10:00"),
        booking(room_id=103, date="2099-10-13"),
    ]
    saved = []
    for payload in payloads:
        response = client.post("/bookings", json=payload)
        assert response.status_code == 201
        saved.append(response.json())
    assert client.get("/bookings", params={"date": DAY}).json() == [
        saved[2],
        saved[1],
        saved[0],
    ]
    assert client.get("/bookings", params={"date": "2099-10-13"}).json() == [saved[3]]


def test_delete_booking_and_missing_id(client):
    response = client.post("/bookings", json=booking())
    assert response.status_code == 201
    booking_id = response.json()["id"]
    deleted = client.delete(f"/bookings/{booking_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/bookings", params={"date": DAY}).json() == []
    assert client.delete(f"/bookings/{booking_id}").status_code == 404


@pytest.mark.parametrize(
    "start,end", [("09:00", "09:30"), ("17:30", "18:00"), ("09:00", "18:00")]
)
def test_working_hours_boundaries_are_valid(client, start, end):
    response = client.post("/bookings", json=booking(start=start, end=end))
    assert response.status_code == 201
    assert response.json()["start"] == start
    assert response.json()["end"] == end


@pytest.mark.parametrize("changes", [
    {"room_id": 999},
    {"title": " \t "},
    {"title": 123},
    {"date": "2099-02-30"},
    {"date": "20991012"},
    {"date": "2099-10-12T00:00:00"},
    {"date": 0},
    {"start": "08:30"},
    {"end": "18:30"},
    {"start": "10:15"},
    {"end": "11:15"},
    {"start": "11:00", "end": "11:00"},
    {"start": "12:00", "end": "11:00"},
    {"start": "10:00:01"},
    {"start": "10:00+03:00"},
    {"start": "invalid-time"},
    {"end": "25:00"},
])
def test_invalid_booking_is_rejected_without_saving(client, changes):
    response = client.post("/bookings", json=booking(**changes))
    assert response.status_code == 422
    assert client.get("/bookings", params={"date": DAY}).json() == []


@pytest.mark.parametrize("field", ["room_id", "title", "date", "start", "end"])
def test_missing_booking_field_is_rejected(client, field):
    payload = booking()
    del payload[field]
    assert client.post("/bookings", json=payload).status_code == 422
    assert client.get("/bookings", params={"date": DAY}).json() == []


@pytest.mark.parametrize(
    "params", [{}, {"date": "invalid"}, {"date": "2099-02-30"}, {"date": "20991012"}]
)
def test_list_requires_valid_date(client, params):
    assert client.get("/bookings", params=params).status_code == 422


def test_separate_databases_are_isolated(client, tmp_path):
    assert client.post("/bookings", json=booking()).status_code == 201
    with TestClient(create_app(tmp_path / "other.sqlite3")) as other:
        assert other.get("/bookings", params={"date": DAY}).json() == []


def test_database_path_can_be_set_with_environment(tmp_path, monkeypatch):
    path = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("ROOMBOOK_DB", str(path))
    with TestClient(create_app()) as session:
        assert session.post("/bookings", json=booking()).status_code == 201
    with TestClient(create_app(path)) as restarted:
        assert len(restarted.get("/bookings", params={"date": DAY}).json()) == 1


def test_swagger_and_openapi_are_available(client):
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "RoomBook"
    assert {"/rooms", "/bookings", "/bookings/{booking_id}"} <= response.json()[
        "paths"
    ].keys()


# === Feature A: запрет пересечений ===
# Тесты следуют правилам writing-good-tests.md: проверяем реальное поведение API,
# ожидания заданы явно, без вычисления ожидаемого результата кодом приложения.


def test_conflict_partial_overlap_returns_409_and_does_not_save(client):
    # Базовая запись 10:00–11:00
    first = client.post("/bookings", json=booking()).json()
    # Частичное пересечение: 10:30–11:30
    response = client.post("/bookings", json=booking(start="10:30", end="11:30"))
    assert response.status_code == 409
    assert response.json() == {
        "detail": {"reason": "overlap", "conflict_id": first["id"]}
    }
    # Состав базы не меняется
    assert client.get("/bookings", params={"date": DAY}).json() == [first]


def test_conflict_nested_interval_returns_409(client):
    first = client.post("/bookings", json=booking()).json()
    # Вложенный интервал внутри [10:00, 11:00): 10:30–11:00
    response = client.post("/bookings", json=booking(start="10:30", end="11:00"))
    assert response.status_code == 409
    assert response.json() == {
        "detail": {"reason": "overlap", "conflict_id": first["id"]}
    }


def test_conflict_full_duplicate_returns_409(client):
    first = client.post("/bookings", json=booking()).json()
    # Полный дубль 10:00–11:00
    response = client.post("/bookings", json=booking())
    assert response.status_code == 409
    assert response.json() == {
        "detail": {"reason": "overlap", "conflict_id": first["id"]}
    }


def test_adjacent_intervals_are_allowed(client):
    first = client.post("/bookings", json=booking()).json()
    # Соседний интервал [11:00, 12:00) разрешён
    response = client.post("/bookings", json=booking(start="11:00", end="12:00"))
    assert response.status_code == 201
    second = response.json()
    assert client.get("/bookings", params={"date": DAY}).json() == [first, second]


def test_same_time_other_room_or_date_are_allowed(client):
    # 10:00–11:00 в 101
    first = client.post("/bookings", json=booking()).json()
    # Та же дата и время, другая комната 102 — разрешено
    r_room = client.post("/bookings", json=booking(room_id=102))
    assert r_room.status_code == 201
    second = r_room.json()
    # Та же комната и время, другая дата — разрешено
    r_date = client.post("/bookings", json=booking(date="2099-10-13"))
    assert r_date.status_code == 201
    # Для исходной даты список содержит обе комнаты
    assert client.get("/bookings", params={"date": DAY}).json() == [first, second]
    # Для другой даты — отдельный список
    assert client.get("/bookings", params={"date": "2099-10-13"}).json() == [
        r_date.json()
    ]
