import pytest

from .conftest import DAY


def test_empty_day_returns_all_candidates_in_start_then_room_order(client):
    response = client.get("/api/free-slots", params={"date": DAY, "duration_minutes": 60})
    assert response.status_code == 200
    slots = response.json()
    assert len(slots) == 17 * 3
    assert slots[:3] == [
        {"room_id": room, "date": DAY, "start": "09:00", "end": "10:00"} for room in [101, 102, 103]
    ]
    assert slots[-1] == {"room_id": 103, "date": DAY, "start": "17:00", "end": "18:00"}


def test_busy_day_and_cancellation(client, booking):
    saved = client.post("/api/bookings", json=booking | {"start": "09:00", "end": "18:00"}).json()
    params = {"date": DAY, "duration_minutes": 540, "room_id": 101}
    assert client.get("/api/free-slots", params=params).json() == []
    client.delete(f"/api/bookings/{saved['id']}")
    assert client.get("/api/free-slots", params=params).json() == [
        {"room_id": 101, "date": DAY, "start": "09:00", "end": "18:00"}
    ]


def test_free_slots_respect_booking_boundaries_and_do_not_change_schedule(client, booking):
    saved = client.post("/api/bookings", json=booking).json()
    response = client.get(
        "/api/free-slots",
        params={
            "date": DAY,
            "duration_minutes": 60,
            "room_id": 101,
        },
    )
    assert response.status_code == 200
    starts = [slot["start"] for slot in response.json()]
    assert starts == [
        "09:00",
        "11:00",
        "11:30",
        "12:00",
        "12:30",
        "13:00",
        "13:30",
        "14:00",
        "14:30",
        "15:00",
        "15:30",
        "16:00",
        "16:30",
        "17:00",
    ]
    assert client.get("/api/bookings", params={"date": DAY}).json() == [saved]


@pytest.mark.parametrize(
    "change",
    [
        {"duration_minutes": 0},
        {"duration_minutes": 15},
        {"duration_minutes": 45},
        {"duration_minutes": 570},
        {"room_id": 999},
        {"date": "2027-02-30"},
    ],
)
def test_invalid_search(client, change):
    params = {"date": DAY, "duration_minutes": 60} | change
    response = client.get("/api/free-slots", params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
