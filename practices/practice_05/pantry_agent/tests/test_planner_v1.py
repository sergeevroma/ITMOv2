import pytest

from planner import plan_recipes, load_recipes, load_substitutions


def test_load_recipes_tags_and_cost(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "recipes.json").write_text(
        "[{\n  \"name\": \"X\", \"ingredients\": [\"a\"], \"tags\": [\"T\"], \"cost\": 1.5\n}]",
        encoding="utf-8",
    )
    data = load_recipes(data_dir)
    assert data[0]["name"] == "X"
    assert data[0]["tags"] == ["t"]  # normalized tags
    assert data[0]["cost"] == 1.5


def test_load_recipes_validation_errors(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # empty ingredients
    (data_dir / "recipes.json").write_text(
        "[{\n  \"name\": \"X\", \"ingredients\": []\n}]",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_recipes(data_dir)
    # negative cost
    (data_dir / "recipes.json").write_text(
        "[{\n  \"name\": \"X\", \"ingredients\": [\"a\"], \"cost\": -1\n}]",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_recipes(data_dir)


def test_load_substitutions_reading(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # missing file -> {}
    assert load_substitutions(data_dir) == {}
    # with file
    (data_dir / "substitutions.json").write_text(
        "{\n  \"scallion\": [\"Green Onion\"]\n}",
        encoding="utf-8",
    )
    subs = load_substitutions(data_dir)
    assert subs == {"scallion": ["green onion"]}


def test_plan_with_allow_missing_and_score():
    recipes = [
        {"name": "A", "ingredients": ["x", "y"], "cost": 0},
        {"name": "B", "ingredients": ["x"], "cost": 0},
    ]
    res = plan_recipes(["x"], recipes, limit=10, allow_missing=1)
    # Both allowed; score for B should be higher -> B first
    assert [r["name"] for r in res] == ["B", "A"]
    assert res[0]["missing"] == []
    assert res[1]["missing"] == ["y"]
    assert isinstance(res[0]["score"], float)


def test_plan_with_diet_tags_and_cost_and_subs(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "substitutions.json").write_text(
        "{\n  \"scallion\": [\"green onion\"]\n}",
        encoding="utf-8",
    )
    subs = load_substitutions(data_dir)
    recipes = [
        {"name": "Salad", "ingredients": ["Scallion"], "tags": ["vegetarian"], "cost": 1.0},
        {"name": "Pasta", "ingredients": ["garlic"], "tags": ["vegetarian"], "cost": 5.0},
    ]
    res = plan_recipes(
        ["green onion"],
        recipes,
        limit=10,
        allow_missing=0,
        diet_tags=["Vegetarian"],
        max_cost=3.0,
        use_substitutions=True,
        substitutions=subs,
    )
    assert [r["name"] for r in res] == ["Salad"]
    assert res[0]["used_substitutions"] == ["scallion<-green onion"]
