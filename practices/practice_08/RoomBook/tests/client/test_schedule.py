from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from ..conftest import DAY


def test_loads_rooms_rules_and_schedule(page, live_server, mocked_config):
    page.route("**/api/bookings**", lambda route: route.fulfill(json=live_server["bookings"]))
    page.goto(live_server["url"])
    expect(page.get_by_role("radio", name="Комната 101", exact=True)).to_be_visible()
    expect(page.get_by_text("Мест: 4", exact=True)).to_be_visible()
    expect(page.get_by_label("Дата бронирования")).to_have_value(DAY)
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    expect(page.locator(".schedule-booking")).to_have_count(2)
    expect(page.get_by_role("heading", name="Анна Смирнова")).to_be_visible()
    expect(page.locator("#schedule-date")).to_have_text("Понедельник, 15 марта")
    assert page.locator("#booking-start option").all_text_contents()[1:] == [
        "09:00",
        "09:30",
        "10:00",
        "10:30",
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
        "17:30",
    ]
    expect(page.get_by_role("button", name="Забронировать", exact=True)).to_be_disabled()


def test_filters_are_independent_from_form_and_update_count(page, live_server, mocked_config):
    queries = []

    def respond(route):
        query = parse_qs(urlparse(route.request.url).query)
        queries.append(query)
        records = [r for r in live_server["bookings"] if r["date"] == query["date"][0]]
        if "room_id" in query:
            records = [r for r in records if r["room_id"] == int(query["room_id"][0])]
        route.fulfill(json=records)

    page.route("**/api/bookings**", respond)
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    page.get_by_role("radio", name="Комната 101", exact=True).check()
    page.get_by_label("ФИО организатора").fill("Мария Петрова")
    page.get_by_role("combobox", name="Комната", exact=True).select_option("103")
    expect(page.locator("#booking-count")).to_have_text("1 бронь")
    expect(page.get_by_role("heading", name="Максим Кузнецов")).to_be_visible()
    expect(page.get_by_role("heading", name="Анна Смирнова")).to_have_count(0)
    expect(page.get_by_role("radio", name="Комната 101", exact=True)).to_be_checked()
    page.get_by_label("Дата бронирования").fill("2027-03-16")
    expect(page.get_by_role("heading", name="Пока нет броней", exact=True)).to_be_visible()
    expect(page.locator("#booking-count")).to_have_text("0 броней")
    expect(page.get_by_label("ФИО организатора")).to_have_value("Мария Петрова")
    assert queries == [
        {"date": [DAY]},
        {"date": [DAY], "room_id": ["103"]},
        {"date": ["2027-03-16"], "room_id": ["103"]},
    ]


def test_loading_then_empty_response(page, live_server, mocked_config):
    held = []
    page.route("**/api/bookings**", lambda route: held.append(route))
    page.goto(live_server["url"])
    expect(page.get_by_text("Загружаем расписание…", exact=True)).to_be_visible()
    expect(page.locator("#schedule-panel")).to_have_attribute("aria-busy", "true")
    expect(page.locator(".schedule-booking")).to_have_count(0)
    assert len(held) == 1
    held[0].fulfill(json=[])
    expect(page.get_by_role("heading", name="Пока нет броней", exact=True)).to_be_visible()
    expect(page.locator("#booking-count")).to_have_text("0 броней")
    expect(page.locator("#schedule-panel")).to_have_attribute("aria-busy", "false")


@pytest.mark.parametrize("failure", ["http", "network", "json"])
def test_schedule_error_can_be_retried(page, live_server, mocked_config, failure):
    calls = []

    def respond(route):
        calls.append(route.request.url)
        if len(calls) > 1:
            route.fulfill(json=live_server["bookings"])
        elif failure == "http":
            route.fulfill(status=503, json={"error": {"code": "unavailable", "message": "Ошибка"}})
        elif failure == "network":
            route.abort()
        else:
            route.fulfill(content_type="application/json", body="not json")

    page.route("**/api/bookings**", respond)
    page.goto(live_server["url"])
    expect(page.get_by_role("alert")).to_contain_text("Не удалось загрузить расписание")
    page.get_by_role("button", name="Повторить", exact=True).click()
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    expect(page.get_by_role("alert")).to_have_count(0)
    assert len(calls) == 2


def test_configuration_error_can_be_retried(page, live_server):
    calls = []

    def rooms(route):
        calls.append(route.request.url)
        if len(calls) == 1:
            route.fulfill(
                status=500, json={"error": {"code": "internal_error", "message": "Ошибка"}}
            )
        else:
            route.fulfill(json=live_server["rooms"])

    page.route("**/api/rooms", rooms)
    page.route("**/api/booking-rules", lambda route: route.fulfill(json=live_server["rules"]))
    page.route("**/api/bookings**", lambda route: route.fulfill(json=[]))
    page.goto(live_server["url"])
    expect(page.get_by_role("alert")).to_contain_text("Не удалось загрузить комнаты")
    expect(page.get_by_label("Дата бронирования")).to_be_disabled()
    page.get_by_role("button", name="Повторить", exact=True).click()
    expect(page.get_by_role("heading", name="Пока нет броней", exact=True)).to_be_visible()
    expect(page.get_by_role("radio")).to_have_count(3)
    assert len(calls) == 2


def test_new_filter_aborts_previous_request(page, live_server, mocked_config):
    held = []

    def respond(route):
        query = parse_qs(urlparse(route.request.url).query)
        if query.get("room_id") == ["101"]:
            held.append(route)
        elif query.get("room_id") == ["103"]:
            route.fulfill(json=[live_server["bookings"][1]])
        else:
            route.fulfill(json=live_server["bookings"])

    page.route("**/api/bookings**", respond)
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    page.get_by_role("combobox", name="Комната", exact=True).select_option("101")
    expect(page.get_by_text("Загружаем расписание…", exact=True)).to_be_visible()
    assert len(held) == 1
    with page.expect_event("requestfailed", predicate=lambda request: "room_id=101" in request.url):
        page.get_by_role("combobox", name="Комната", exact=True).select_option("103")
    expect(page.locator("#booking-count")).to_have_text("1 бронь")
    expect(page.get_by_role("heading", name="Максим Кузнецов")).to_be_visible()
    expect(page.get_by_role("heading", name="Анна Смирнова")).to_have_count(0)


def test_cleared_date_does_not_request_schedule(page, live_server, mocked_config):
    calls = []

    def respond(route):
        calls.append(route.request.url)
        route.fulfill(json=[])

    page.route("**/api/bookings**", respond)
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("0 броней")
    page.get_by_label("Дата бронирования").fill("")
    expect(page.get_by_role("heading", name="Выберите дату", exact=True)).to_be_visible()
    expect(page.locator("#booking-count")).to_have_text("—")
    assert len(calls) == 1


def test_reads_real_api(page, live_server):
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    page.get_by_role("combobox", name="Комната", exact=True).select_option("101")
    expect(page.locator("#booking-count")).to_have_text("1 бронь")
    expect(page.get_by_role("heading", name="Анна Смирнова")).to_be_visible()


@pytest.mark.parametrize("width", [390, 1440, 2560])
def test_layout_and_keyboard_navigation(page, live_server, mocked_config, width):
    page.set_viewport_size({"width": width, "height": 960})
    page.route("**/api/bookings**", lambda route: route.fulfill(json=live_server["bookings"]))
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    form = page.locator(".booking-panel").bounding_box()
    schedule = page.locator(".schedule-panel").bounding_box()
    if width < 992:
        assert schedule["y"] > form["y"] + form["height"]
    else:
        assert schedule["x"] > form["x"] + form["width"]
    page.get_by_role("radio", name="Комната 101", exact=True).focus()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_role("radio", name="Комната 102", exact=True)).to_be_checked()
    page.keyboard.press("Tab")
    expect(page.get_by_label("ФИО организатора")).to_be_focused()
