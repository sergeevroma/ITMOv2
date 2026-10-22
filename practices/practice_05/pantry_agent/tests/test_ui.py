import json

import pytest

from app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_get_index_and_fields(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "<form" in html
    for name in ["pantry", "limit", "allow_missing", "diet_tags", "max_cost", "use_substitutions"]:
        assert name in html


def test_success_selection_and_defaults(client):
    # pantry only, defaults used for others
    resp = client.post(
        "/",
        data={
            "pantry": "egg, milk, salt",
            # leave others empty to test defaults
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Результаты" in html
    assert "Omelet" in html


def test_transform_all_params_and_parity_with_api(client):
    # Use tags/cost/substitutions case: rely on existing data where tags may be empty; focus on transform/parity
    # Send via UI
    ui_form = {
        "pantry": "egg\n  salt  ",
        "limit": "5",
        "allow_missing": "1",
        "diet_tags": "vegetarian,breakfast, ,",
        "max_cost": "5.5",
        "use_substitutions": "on",
    }
    ui_resp = client.post("/", data=ui_form)
    assert ui_resp.status_code == 200
    html = ui_resp.data.decode("utf-8")
    assert "Результаты" in html

    # Derive API payload as the server should parse it
    payload = {
        "pantry": ["egg", "salt"],
        "limit": 5,
        "allow_missing": 1,
        "diet_tags": ["vegetarian", "breakfast"],
        "max_cost": 5.5,
        "use_substitutions": True,
    }
    api_resp = client.post("/v1/plan", data=json.dumps(payload), content_type="application/json")
    assert api_resp.status_code == 200
    # Compare ordered names appearing in HTML in the same order as API
    api_names = [r["name"] for r in api_resp.get_json()["recipes"]]
    # Ensure HTML contains them in order
    last_idx = -1
    for name in api_names:
        idx = html.find(name)
        assert idx != -1
        assert idx > last_idx
        last_idx = idx


def test_errors_and_preserve_inputs(client):
    # invalid limit
    resp = client.post(
        "/",
        data={
            "pantry": "egg",
            "limit": "0",
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "limit must be int >= 1" in html
    # input preserved
    assert "egg" in html
    assert "value=\"0\"" in html


def test_empty_result_message(client):
    # Use pantry unlikely to match any recipe strictly
    resp = client.post("/", data={"pantry": "unknown_ingredient"})
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Нет подходящих рецептов" in html
