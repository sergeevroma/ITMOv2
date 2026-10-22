from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


DATA_DIR = Path(__file__).resolve().parent / "data"


def _normalize_token(token: str) -> str:
    # Normalize tokens: strip spaces and lower case
    return token.strip().lower()


def load_recipes(data_dir: Optional[Path] = None) -> List[Dict]:
    """Load recipes from data/recipes.json.

    Each recipe is a dict with keys: name (str), ingredients (List[str]).
    V1: supports optional tags (List[str]) and cost (number). Applies defaults
    tags=[] and cost=0.0 when absent. Validates that each recipe has at least
    one non-empty ingredient (post-strip) and cost >= 0.
    """
    dir_to_use = DATA_DIR if data_dir is None else data_dir
    with (dir_to_use / "recipes.json").open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Basic validation to keep tests deterministic
    if not isinstance(data, list):
        raise ValueError("recipes.json must be a list")
    validated: List[Dict] = []
    for r in data:
        if not isinstance(r, dict) or "name" not in r or "ingredients" not in r:
            raise ValueError("invalid recipe entry")
        name = r.get("name")
        ings = r.get("ingredients")
        if not isinstance(name, str):
            raise ValueError("invalid recipe name")
        if not isinstance(ings, list) or any(not isinstance(x, str) for x in ings):
            raise ValueError("invalid ingredients list")
        # Ensure at least one non-empty ingredient (after strip())
        non_empty = [x for x in ings if _normalize_token(x) != ""]
        if len(non_empty) == 0:
            raise ValueError("recipe must have at least one non-empty ingredient")
        tags = r.get("tags", [])
        if tags is None:
            tags = []
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise ValueError("invalid tags")
        cost = r.get("cost", 0.0)
        if not isinstance(cost, (int, float)):
            raise ValueError("invalid cost type")
        if cost < 0:
            raise ValueError("cost must be >= 0")
        # normalize tags for consistent matching; keep original ingredients as-is
        normalized_tags = [_normalize_token(t) for t in tags]
        validated.append({
            "name": name,
            "ingredients": ings,
            "tags": normalized_tags,
            "cost": float(cost),
        })
    return validated


def load_substitutions(data_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load substitutions mapping from data/substitutions.json.

    Returns mapping of normalized recipe ingredient -> list of normalized pantry tokens.
    Missing file means no substitutions.
    """
    dir_to_use = DATA_DIR if data_dir is None else data_dir
    path = dir_to_use / "substitutions.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("substitutions.json must be a dict")
    result: Dict[str, List[str]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, list) or any(not isinstance(x, str) for x in v):
            raise ValueError("invalid substitutions entry")
        key = _normalize_token(k)
        vals = [_normalize_token(x) for x in v]
        result[key] = vals
    return result


def plan_recipes(
    pantry: List[str],
    recipes: List[Dict],
    limit: int = 10,
    allow_missing: int = 0,
    diet_tags: Optional[List[str]] = None,
    max_cost: Optional[float] = None,
    use_substitutions: bool = False,
    substitutions: Optional[Dict[str, List[str]]] = None,
) -> List[Dict]:
    """Plan recipes given pantry and options.

    Returns enriched recipe dicts including missing, used_substitutions, tags, cost, score.
    """
    if not isinstance(pantry, list) or any(not isinstance(x, str) for x in pantry):
        raise TypeError("pantry must be a list of strings")
    if not pantry:
        raise ValueError("pantry must be non-empty")
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be int >= 1")
    if not isinstance(allow_missing, int) or allow_missing < 0:
        raise ValueError("allow_missing must be int >= 0")
    if diet_tags is None:
        diet_tags = []
    if not isinstance(diet_tags, list) or any(not isinstance(t, str) for t in diet_tags):
        raise ValueError("diet_tags must be a list of strings")
    if max_cost is not None and not isinstance(max_cost, (int, float)):
        raise ValueError("max_cost must be a number >= 0 or None")
    if max_cost is not None and max_cost < 0:
        raise ValueError("max_cost must be a number >= 0 or None")
    if not isinstance(use_substitutions, bool):
        raise ValueError("use_substitutions must be a bool")

    normalized_pantry = {_normalize_token(x) for x in pantry}
    normalized_diet = [_normalize_token(t) for t in diet_tags]
    subs = substitutions or {}

    def assess_recipe(recipe: Dict) -> Tuple[bool, Dict]:
        # Unique normalized ingredients order preserving
        raw_ings = recipe.get("ingredients", [])
        norm_ings = []
        seen = set()
        for i in raw_ings:
            ni = _normalize_token(i)
            if ni not in seen:
                seen.add(ni)
                norm_ings.append(ni)

        missing: List[str] = []
        used_subs: List[str] = []
        covered_count = 0
        for ing in norm_ings:
            if ing in normalized_pantry:
                covered_count += 1
                continue
            used = False
            if use_substitutions and ing in subs:
                for cand in subs[ing]:
                    if cand in normalized_pantry:
                        used_subs.append(f"{ing}<-{cand}")
                        covered_count += 1
                        used = True
                        break
            if not used:
                missing.append(ing)

        total = len(norm_ings) if norm_ings else 1  # guard divide by zero, though validated
        cost = float(recipe.get("cost", 0.0))
        score = (covered_count / total) - 0.5 * (len(missing) / total) - 0.1 * (min(cost, 10) / 10)
        # round score to 3 decimals for output
        rounded_score = round(score + 0.0, 3)

        tags = recipe.get("tags", [])
        # Filter by tags and cost
        has_tags = all(t in tags for t in normalized_diet)
        if not has_tags:
            return False, {}
        if max_cost is not None and cost > float(max_cost):
            return False, {}
        if len(missing) > allow_missing:
            return False, {}

        enriched = {
            "name": recipe.get("name"),
            "ingredients": recipe.get("ingredients", []),
            "missing": missing,
            "used_substitutions": used_subs,
            "tags": tags,
            "cost": cost,
            "score": rounded_score,
        }
        return True, enriched

    results: List[Dict] = []
    for r in recipes:
        ok, enriched = assess_recipe(r)
        if ok:
            results.append(enriched)

    # Sorting
    extensions_enabled = (
        (allow_missing > 0)
        or (len(normalized_diet) > 0)
        or (max_cost is not None)
        or use_substitutions
    )
    if extensions_enabled:
        results.sort(key=lambda d: (-d.get("score", 0.0), d.get("name", "")))
    else:
        # Maintain V0 strict behavior: only fully covered should have passed anyway
        results.sort(key=lambda d: d.get("name", ""))
    return results[:limit]
