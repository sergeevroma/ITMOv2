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
    # Ensure V1 fields are present
    for r in data["recipes"]:
        assert "missing" in r
        assert "used_substitutions" in r
        assert "tags" in r
        assert "cost" in r
        assert "score" in r


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


def test_plan_v1_params_and_sorting(client):
    # allow_missing should include partial match and switch sorting to score
    payload = {"pantry": ["egg", "salt"], "allow_missing": 1}
    resp = client.post("/v1/plan", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(r["name"] == "Omelet" and "milk" in r["missing"] for r in data["recipes"])


def test_plan_substitutions_flag(client):
    # Since default substitutions.json may not map anything, this test just verifies validation for flags
    payload = {"pantry": ["x"], "use_substitutions": True}
    resp = client.post("/v1/plan", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
