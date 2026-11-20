import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

from roombook.main import create_app

from ..conftest import DAY


def pytest_addoption(parser):
    parser.addoption("--evidence-dir", help="Сохранить скриншоты проверяемых состояний")


@pytest.fixture
def capture(page, request):
    def save(name):
        directory = request.config.getoption("--evidence-dir")
        if directory:
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(target / name), full_page=True, animations="disabled")

    return save


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server["url"]


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "locale": "ru-RU",
        "timezone_id": "UTC",
        "viewport": {"width": 1440, "height": 960},
    }


@pytest.fixture(autouse=True)
def browser_clock_and_errors(page):
    # В UTC ещё 14 марта, в Москве уже 15-е: дата должна следовать правилам API.
    page.clock.set_fixed_time(datetime(2027, 3, 14, 22, tzinfo=UTC))
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield
    assert not errors, errors


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    application = create_app(tmp_path_factory.mktemp("browser") / "bookings.sqlite3")
    with TestClient(application) as client:
        rooms = client.get("/api/rooms").json()
        rules = client.get("/api/booking-rules").json()
        bookings = []
        for record in [
            {
                "room_id": 101,
                "organizer": "Анна Смирнова",
                "title": "Подготовка к семинару",
                "date": DAY,
                "start": "10:00",
                "end": "11:30",
            },
            {
                "room_id": 103,
                "organizer": "Максим Кузнецов",
                "title": "Учебный проект",
                "date": DAY,
                "start": "14:00",
                "end": "16:00",
            },
        ]:
            response = client.post("/api/bookings", json=record)
            assert response.status_code == 201
            bookings.append(response.json())

    with socket.socket() as listening:
        listening.bind(("127.0.0.1", 0))
        port = listening.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                application,
                log_level="warning",
                timeout_graceful_shutdown=2,
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listening]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Тестовый сервер не запустился")
                time.sleep(0.01)
            yield {
                "url": f"http://127.0.0.1:{port}",
                "rooms": rooms,
                "rules": rules,
                "bookings": bookings,
            }
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "Тестовый сервер не остановился"


@pytest.fixture
def mocked_config(page, live_server):
    page.route("**/api/rooms", lambda route: route.fulfill(json=live_server["rooms"]))
    page.route("**/api/booking-rules", lambda route: route.fulfill(json=live_server["rules"]))
