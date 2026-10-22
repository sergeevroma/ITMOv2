import pytest

from planner import plan_recipes, load_recipes


def test_plan_recipes_strict_match():
    recipes = [
        {"name": "A", "ingredients": ["x", "y"]},
        {"name": "B", "ingredients": ["x"]},
        {"name": "C", "ingredients": ["X", "Z"]},
    ]
    res = plan_recipes(["x", "y", "z"], recipes, limit=10)
    # Only A (x,y) and B (x) should match strictly; C requires z and x but has Z case
    # Note: normalization makes case-insensitive, so C requires x and z; pantry has both -> C also matches
    # Correct expected: A, B, C; sorted by name
    assert [r["name"] for r in res] == ["A", "B", "C"]


def test_plan_recipes_limit_and_sort():
    recipes = [
        {"name": "C", "ingredients": ["x"]},
        {"name": "B", "ingredients": ["x"]},
        {"name": "A", "ingredients": ["x"]},
    ]
    res = plan_recipes(["x"], recipes, limit=2)
    assert [r["name"] for r in res] == ["A", "B"]


def test_invalid_inputs():
    recipes = []
    with pytest.raises(TypeError):
        plan_recipes("x", recipes)
    with pytest.raises(ValueError):
        plan_recipes([], recipes)
    with pytest.raises(ValueError):
        plan_recipes(["x"], recipes, limit=0)


def test_load_recipes_reads_default_file(tmp_path):
    # Create a temporary data dir with a recipes.json
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "recipes.json").write_text("[{\n  \"name\": \"X\", \"ingredients\": [\"a\"]\n}]", encoding="utf-8")
    data = load_recipes(data_dir)
    assert data[0]["name"] == "X"
