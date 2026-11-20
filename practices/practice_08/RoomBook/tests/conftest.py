import pytest
from fastapi.testclient import TestClient

from roombook.main import create_app

DAY = "2027-03-15"


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "data" / "bookings.sqlite3"


@pytest.fixture
def client(database_path):
    with TestClient(create_app(database_path)) as session:
        yield session


@pytest.fixture
def booking():
    return {
        "room_id": 101,
        "organizer": "Роман Сергеев",
        "title": "Подготовка к защите",
        "date": DAY,
        "start": "10:00",
        "end": "11:00",
    }
