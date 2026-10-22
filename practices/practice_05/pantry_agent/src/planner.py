from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


DATA_DIR = Path(__file__).resolve().parent / "data"


def _normalize_token(token: str) -> str:
    # Normalize ingredient tokens: strip spaces and lower case
    return token.strip().lower()


def load_recipes(data_dir: Path | None = None) -> List[Dict]:
    """Load recipes from data/recipes.json.

    Each recipe is a dict with keys: name (str), ingredients (List[str]).
    """
    dir_to_use = DATA_DIR if data_dir is None else data_dir
    with (dir_to_use / "recipes.json").open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Basic validation to keep tests deterministic
    if not isinstance(data, list):
        raise ValueError("recipes.json must be a list")
    for r in data:
        if not isinstance(r, dict) or "name" not in r or "ingredients" not in r:
            raise ValueError("invalid recipe entry")
    return data


def plan_recipes(pantry: List[str], recipes: List[Dict], limit: int = 10) -> List[Dict]:
    """Return recipes that can be cooked strictly with given pantry.

    - pantry: list of ingredient strings.
    - recipes: list of recipe dicts {name, ingredients}.
    - limit: max number of recipes to return.
    """
    if not isinstance(pantry, list) or any(not isinstance(x, str) for x in pantry):
        raise TypeError("pantry must be a list of strings")
    if not pantry:
        raise ValueError("pantry must be non-empty")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be int >= 1")

    normalized_pantry = {_normalize_token(x) for x in pantry}

    def recipe_ok(recipe: Dict) -> Tuple[bool, List[str]]:
        ings = [_normalize_token(i) for i in recipe.get("ingredients", [])]
        missing = [i for i in ings if i not in normalized_pantry]
        return (len(missing) == 0, missing)

    ok_recipes = []
    for r in recipes:
        ok, missing = recipe_ok(r)
        if ok:
            ok_recipes.append(r)

    # Deterministic order: sort by recipe name
    ok_recipes.sort(key=lambda d: d.get("name", ""))
    return ok_recipes[:limit]
