import re

import pytest
from playwright.sync_api import expect

from ..conftest import DAY


@pytest.fixture
def booking_api(page, live_server, mocked_config):
    records = []
    calls = []

    def respond(route):
        request = route.request
        calls.append(request)
        if request.method == "GET":
            route.fulfill(json=records)
        elif request.method == "POST":
            record = {**request.post_data_json, "id": 1001}
            records.append(record)
            route.fulfill(status=201, json=record)
        elif request.method == "DELETE":
            records.clear()
            route.fulfill(status=204)

    page.route("**/api/bookings**", respond)
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("0 броней")
    return {"records": records, "calls": calls}


def fill_booking(page, omit=None):
    if omit != "room_id":
        page.get_by_role("radio", name="Комната 102", exact=True).check()
    if omit != "organizer":
        page.get_by_label("ФИО организатора").fill("Мария Петрова")
    if omit != "title":
        page.get_by_label("Цель встречи").fill("Подготовка доклада")
    if omit != "start":
        page.get_by_label("Начало", exact=True).select_option("12:00")
    if omit != "end":
        page.get_by_label("Окончание", exact=True).select_option("13:00")


def submit(page):
    page.get_by_role("button", name="Забронировать", exact=True).click()


def test_creates_booking_resets_form_and_reveals_filtered_room(page, booking_api, capture):
    capture("empty.png")
    page.get_by_role("combobox", name="Комната", exact=True).select_option("103")
    expect(page.locator("#schedule-panel")).to_have_attribute("aria-busy", "false")
    fill_booking(page)
    page.get_by_label("ФИО организатора").fill("  Мария Петрова  ")
    capture("filled.png")
    submit(page)
    expect(page.locator("#action-success")).to_contain_text("Бронь создана: комната 102")
    expect(page.get_by_role("heading", name="Мария Петрова")).to_be_visible()
    expect(page.locator(".new-booking")).to_contain_text("Подготовка доклада")
    expect(page.locator("#booking-count")).to_have_text("1 бронь")
    expect(page.get_by_role("combobox", name="Комната", exact=True)).to_have_value("")
    expect(page.get_by_label("ФИО организатора")).to_be_empty()
    expect(page.get_by_label("Цель встречи")).to_be_empty()
    expect(page.get_by_label("Начало", exact=True)).to_have_value("")
    expect(page.get_by_label("Дата бронирования")).to_have_value(DAY)
    posts = [request for request in booking_api["calls"] if request.method == "POST"]
    assert len(posts) == 1
    assert posts[0].post_data_json == {
        "room_id": 102,
        "organizer": "Мария Петрова",
        "title": "Подготовка доклада",
        "date": DAY,
        "start": "12:00",
        "end": "13:00",
    }
    capture("success.png")


@pytest.mark.parametrize("field", ["room_id", "organizer", "title", "date", "start", "end"])
def test_required_field_shows_error_without_post(page, booking_api, field):
    fill_booking(page, omit=field)
    if field == "date":
        page.get_by_label("Дата бронирования").fill("")
    submit(page)
    expect(page.locator(f'[data-field-error="{field}"]')).to_be_visible()
    expect(page.locator("#form-error")).to_contain_text("Проверьте выделенные поля")
    assert not [request for request in booking_api["calls"] if request.method == "POST"]


@pytest.mark.parametrize("field", ["organizer", "title"])
def test_whitespace_is_not_valid_text(page, booking_api, field):
    fill_booking(page)
    page.locator(f'[name="{field}"]').fill("   ")
    submit(page)
    expect(page.locator(f'[data-field-error="{field}"]')).to_have_text("Заполните поле.")
    expect(page.locator(f'[name="{field}"]')).to_have_attribute("aria-invalid", "true")
    assert not [request for request in booking_api["calls"] if request.method == "POST"]


@pytest.mark.parametrize("end", ["11:30", "12:00"])
def test_end_must_follow_start_and_can_be_corrected(page, booking_api, end, capture):
    fill_booking(page)
    page.get_by_label("Окончание", exact=True).select_option(end)
    submit(page)
    expect(page.locator("#end-error")).to_have_text("Окончание должно быть позже начала.")
    expect(page.get_by_label("Окончание", exact=True)).to_be_focused()
    if end == "11:30":
        capture("validation.png")
    assert not [request for request in booking_api["calls"] if request.method == "POST"]
    page.get_by_label("Окончание", exact=True).select_option("13:00")
    expect(page.locator("#end-error")).to_be_hidden()
    submit(page)
    expect(page.locator("#action-success")).to_contain_text("Бронь создана")


def test_repeated_click_and_enter_send_only_one_post_while_waiting(page, booking_api, capture):
    held = []
    page.route(re.compile(r"/api/bookings$"), lambda route: held.append(route))
    fill_booking(page)
    page.get_by_role("button", name="Забронировать", exact=True).click(click_count=2)
    expect(page.get_by_role("button", name="Бронируем…")).to_be_disabled()
    expect(page.locator("#submit-spinner")).to_be_visible()
    expect(page.locator("#booking-form")).to_have_attribute("aria-busy", "true")
    expect(page.get_by_label("Дата бронирования")).to_be_disabled()
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    # Дополнительно проверяем защиту обработчика, помимо disabled в HTML.
    page.locator("#booking-form").dispatch_event("submit")
    assert len(held) == 1
    capture("loading.png")
    record = {**held[0].request.post_data_json, "id": 1001}
    booking_api["records"].append(record)
    held[0].fulfill(status=201, json=record)
    expect(page.get_by_role("heading", name="Мария Петрова")).to_be_visible()
    expect(page.get_by_role("button", name="Забронировать", exact=True)).to_be_enabled()
    expect(page.locator("#booking-form")).to_have_attribute("aria-busy", "false")
    assert len(held) == 1


@pytest.mark.parametrize("failure", ["conflict", "validation", "http", "network", "json"])
def test_save_error_preserves_input_and_allows_retry(page, booking_api, failure, capture):
    calls = []
    if failure == "conflict":
        booking_api["records"].append(
            {
                "id": 1000,
                "room_id": 102,
                "organizer": "Олег Иванов",
                "title": "Консультация",
                "date": DAY,
                "start": "12:00",
                "end": "13:00",
            }
        )
        page.reload()
        expect(page.locator("#booking-count")).to_have_text("1 бронь")
        expect(page.get_by_role("heading", name="Олег Иванов")).to_be_visible()

    def fail_once(route):
        calls.append(route.request)
        if len(calls) > 1:
            record = {**route.request.post_data_json, "id": 1001}
            booking_api["records"].append(record)
            route.fulfill(status=201, json=record)
        elif failure == "conflict":
            route.fulfill(
                status=409,
                json={"error": {"code": "booking_conflict", "message": "Комната уже занята."}},
            )
        elif failure == "validation":
            route.fulfill(
                status=422,
                json={
                    "error": {
                        "code": "validation_error",
                        "message": "Проверьте введённые данные.",
                        "fields": {"organizer": "Уточните имя организатора."},
                    }
                },
            )
        elif failure == "http":
            route.fulfill(status=503, body="Unavailable")
        elif failure == "json":
            route.fulfill(status=201, content_type="application/json", body="not json")
        else:
            route.abort()

    page.route(re.compile(r"/api/bookings$"), fail_once)
    fill_booking(page)
    submit(page)
    expected = {
        "conflict": "Комната уже занята",
        "validation": "Проверьте введённые данные",
    }.get(failure, "бронь могла сохраниться")
    expect(page.locator("#form-error")).to_be_visible()
    expect(page.locator("#form-error")).to_contain_text(expected)
    if failure == "validation":
        expect(page.locator("#organizer-error")).to_have_text("Уточните имя организатора.")
        expect(page.get_by_label("ФИО организатора")).to_be_focused()
    expect(page.get_by_label("ФИО организатора")).to_have_value("Мария Петрова")
    expect(page.get_by_label("Цель встречи")).to_have_value("Подготовка доклада")
    expect(page.get_by_label("Начало", exact=True)).to_have_value("12:00")
    expect(page.get_by_role("radio", name="Комната 102", exact=True)).to_be_checked()
    expect(page.get_by_role("button", name="Забронировать", exact=True)).to_be_enabled()
    if failure == "conflict":
        occupied = page.locator(".schedule-booking").filter(has_text="Олег Иванов")
        expect(occupied).to_contain_text("Комната 102")
        expect(occupied.locator(".booking-time")).to_have_text("12:00–13:00")
        capture("conflict.png")
        page.get_by_label("Начало", exact=True).select_option("13:00")
    page.get_by_label("Окончание", exact=True).select_option("13:30")
    submit(page)
    expect(page.locator("#form-error")).to_be_hidden()
    expect(page.get_by_role("heading", name="Мария Петрова")).to_be_visible()
    assert len(calls) == 2
    if failure == "conflict":
        expect(page.locator("#booking-count")).to_have_text("2 брони")
        assert calls[1].post_data_json["start"] == "13:00"
        assert calls[1].post_data_json["end"] == "13:30"


def test_success_is_kept_if_refresh_fails(page, booking_api):
    fill_booking(page)
    page.route(re.compile(r"/api/bookings\?"), lambda route: route.fulfill(status=503))
    submit(page)
    expect(page.locator("#action-success")).to_contain_text("Бронь создана")
    expect(page.locator("#schedule-error")).to_be_visible()
    expect(page.get_by_label("ФИО организатора")).to_be_empty()


def test_cancellation_waits_once_and_updates_list(page, booking_api):
    fill_booking(page)
    submit(page)
    cancel = page.get_by_role("button", name="Отменить бронь комнаты 102 на 12:00")
    expect(cancel).to_be_visible()
    held = []
    page.route("**/api/bookings/1001", lambda route: held.append(route))
    cancel.click(click_count=2)
    expect(cancel).to_be_disabled()
    expect(cancel).to_have_text("Отменяем…")
    page.keyboard.press("Enter")
    assert len(held) == 1
    assert held[0].request.method == "DELETE"
    booking_api["records"].clear()
    held[0].fulfill(status=204)
    expect(page.locator("#action-success")).to_contain_text("Бронь отменена")
    expect(page.locator(".schedule-booking")).to_have_count(0)
    expect(page.locator("#booking-count")).to_have_text("0 броней")


@pytest.mark.parametrize("missing", [False, True])
def test_cancellation_error_supports_retry_or_refresh(page, booking_api, missing):
    fill_booking(page)
    submit(page)
    cancel = page.get_by_role("button", name="Отменить бронь комнаты 102 на 12:00")
    expect(cancel).to_be_visible()
    calls = []

    def respond(route):
        calls.append(route.request)
        if missing:
            booking_api["records"].clear()
            route.fulfill(
                status=404,
                json={"error": {"code": "booking_not_found", "message": "Бронь не найдена."}},
            )
        elif len(calls) == 1:
            route.abort()
        else:
            booking_api["records"].clear()
            route.fulfill(status=204)

    page.route("**/api/bookings/1001", respond)
    cancel.click()
    expect(page.locator("#action-error")).to_be_visible()
    if missing:
        expect(page.locator("#action-error")).to_contain_text("уже отменена")
        expect(page.locator("#booking-count")).to_have_text("0 броней")
    else:
        expect(cancel).to_be_enabled()
        expect(page.get_by_role("heading", name="Мария Петрова")).to_be_visible()
        cancel.click()
        expect(page.locator("#action-success")).to_contain_text("Бронь отменена")
        expect(page.locator("#action-error")).to_be_hidden()


def test_keyboard_flow_uses_real_api_and_persists_until_cancelled(page, live_server, capture):
    page.goto(live_server["url"])
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    page.get_by_role("radio", name="Комната 102", exact=True).focus()
    page.keyboard.press("Space")
    page.keyboard.press("Tab")
    expect(page.get_by_label("ФИО организатора")).to_be_focused()
    page.keyboard.type("Елена Соколова")
    page.keyboard.press("Tab")
    page.keyboard.type("Обсуждение проекта")
    page.keyboard.press("Tab")
    expect(page.get_by_label("Начало", exact=True)).to_be_focused()
    page.keyboard.press("Home")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Tab")
    page.keyboard.press("Home")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Забронировать", exact=True)).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#action-success")).to_contain_text("Бронь создана")
    expect(page.get_by_role("heading", name="Елена Соколова")).to_be_visible()
    capture("real-api-success.png")
    page.reload()
    expect(page.get_by_role("heading", name="Елена Соколова")).to_be_visible()
    card = page.locator(".schedule-booking").filter(has_text="Елена Соколова")
    card.get_by_role("button").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#action-success")).to_contain_text("Бронь отменена")
    expect(page.get_by_role("heading", name="Елена Соколова")).to_have_count(0)
    page.reload()
    expect(page.locator("#booking-count")).to_have_text("2 брони")
    capture("real-api-cancelled.png")
