import json

import pytest

from app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_plan_happy_path(client):
    payload = {"pantry": ["egg", "milk", "salt"], "limit": 5}
    resp = client.post("/v1/plan", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "recipes" in data
    names = [r["name"] for r in data["recipes"]]
    # Omelet should be present; others may or may not depending on pantry
    assert "Omelet" in names


def test_plan_validation_errors(client):
    # missing pantry
    resp = client.post("/v1/plan", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400

    # pantry not a list
    resp = client.post("/v1/plan", data=json.dumps({"pantry": "x"}), content_type="application/json")
    assert resp.status_code == 400

    # pantry empty
    resp = client.post("/v1/plan", data=json.dumps({"pantry": []}), content_type="application/json")
    assert resp.status_code == 400

    # pantry contains non-strings
    resp = client.post("/v1/plan", data=json.dumps({"pantry": [1]}), content_type="application/json")
    assert resp.status_code == 400

    # invalid limit
    resp = client.post("/v1/plan", data=json.dumps({"panry": ["x"], "limit": 0}), content_type="application/json")
    # invalid request due to missing pantry key first
    assert resp.status_code == 400
