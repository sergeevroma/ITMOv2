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


def has_slot(slots: list[dict], *, room_id: int, start: str, end: str) -> bool:
    for slot in slots:
        if (
            slot["room_id"] == room_id
            and slot["date"] == DAY
            and slot["start"] == start
            and slot["end"] == end
        ):
            return True
    return False


def test_free_slots_empty_day_all_rooms_60min(client):
    response = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 60},
    )
    assert response.status_code == 200
    data = response.json()
    # 09:00..18:00, шаг 30 минут, длительность 60 → последние допустимые старты до 17:00
    # (540 - 60) / 30 + 1 = 17 стартов на комнату, 3 комнаты → 51 интервал
    assert len(data) == 17 * 3
    # Сортировка по началу и комнате
    assert data[0] == {"room_id": 101, "date": DAY, "start": "09:00", "end": "10:00"}
    assert data[1] == {"room_id": 102, "date": DAY, "start": "09:00", "end": "10:00"}
    assert data[2] == {"room_id": 103, "date": DAY, "start": "09:00", "end": "10:00"}
    assert data[-3] == {"room_id": 101, "date": DAY, "start": "17:00", "end": "18:00"}
    assert data[-2] == {"room_id": 102, "date": DAY, "start": "17:00", "end": "18:00"}
    assert data[-1] == {"room_id": 103, "date": DAY, "start": "17:00", "end": "18:00"}


def test_free_slots_single_room_excludes_overlaps_and_keeps_neighbors(client):
    # Занимаем в 101: 10:00–11:00 и 13:30–14:30
    assert client.post("/bookings", json=booking()).status_code == 201
    assert (
        client.post("/bookings", json=booking(start="13:30", end="14:30")).status_code
        == 201
    )
    response = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 30, "room_id": 101},
    )
    assert response.status_code == 200
    slots = response.json()
    # Должны отсутствовать пересекающиеся варианты
    assert not has_slot(slots, room_id=101, start="10:00", end="10:30")
    assert not has_slot(slots, room_id=101, start="10:30", end="11:00")
    assert not has_slot(slots, room_id=101, start="13:30", end="14:00")
    assert not has_slot(slots, room_id=101, start="14:00", end="14:30")
    # Соседние варианты разрешены
    assert has_slot(slots, room_id=101, start="09:00", end="09:30")
    assert has_slot(slots, room_id=101, start="09:30", end="10:00")
    assert has_slot(slots, room_id=101, start="11:00", end="11:30")
    assert has_slot(slots, room_id=101, start="14:30", end="15:00")
    # Только выбранная комната
    assert all(slot["room_id"] == 101 for slot in slots)


def test_free_slots_all_rooms_and_single_room_difference(client):
    # Занимаем 101: 10:00–11:00
    assert client.post("/bookings", json=booking()).status_code == 201
    # По всем комнатам есть варианты на 10:00–11:00 для 102 и 103
    all_rooms = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 60},
    ).json()
    assert has_slot(all_rooms, room_id=102, start="10:00", end="11:00")
    assert has_slot(all_rooms, room_id=103, start="10:00", end="11:00")
    # Для одной комнаты 101 этого варианта быть не должно
    only_101 = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 60, "room_id": 101},
    ).json()
    assert not has_slot(only_101, room_id=101, start="10:00", end="11:00")


def test_free_slots_fully_booked_day_returns_empty(client):
    # Полностью занимаем день во всех комнатах
    for room in (101, 102, 103):
        assert (
            client.post(
                "/bookings", json=booking(room_id=room, start="09:00", end="18:00")
            ).status_code
            == 201
        )
    response = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 60},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"date": DAY},
        {"duration_minutes": 60},
        {"date": "invalid", "duration_minutes": 60},
        {"date": "2099-02-30", "duration_minutes": 60},
        {"date": DAY, "duration_minutes": 0},
        {"date": DAY, "duration_minutes": -30},
        {"date": DAY, "duration_minutes": 25},
        {"date": DAY, "duration_minutes": 541},
        {"date": DAY, "duration_minutes": 60, "room_id": 999},
    ],
)
def test_free_slots_invalid_input_is_rejected(client, params):
    response = client.get("/free-slots", params=params)
    assert response.status_code == 422


def test_free_slots_does_not_modify_bookings(client):
    # Создаём две записи
    b1 = client.post("/bookings", json=booking(start="09:00", end="09:30")).json()
    b2 = client.post("/bookings", json=booking(start="11:00", end="12:00")).json()
    # Поиск свободных слотов
    resp = client.get(
        "/free-slots",
        params={"date": DAY, "duration_minutes": 30},
    )
    assert resp.status_code == 200
    # Расписание не изменилось
    listed = client.get("/bookings", params={"date": DAY})
    assert listed.status_code == 200
    assert listed.json() == [b1, b2]
