from __future__ import annotations

from flask import Flask, jsonify, request, render_template

from planner import plan_recipes, load_recipes, load_substitutions


def create_app() -> Flask:
    app = Flask(__name__)

    # Load data once at startup
    recipes = load_recipes()
    substitutions = load_substitutions()

    @app.route("/v1/plan", methods=["POST"])
    def plan():
        # Validate JSON body
        if not request.is_json:
            return jsonify({"error": "expected application/json"}), 400
        payload = request.get_json()

        pantry = payload.get("pantry")
        limit = payload.get("limit", 10)
        allow_missing = payload.get("allow_missing", 0)
        diet_tags = payload.get("diet_tags", [])
        max_cost = payload.get("max_cost", None)
        use_substitutions = payload.get("use_substitutions", False)

        # Validate inputs explicitly to return 400 instead of 500
        if pantry is None:
            return jsonify({"error": "pantry is required"}), 400
        if not isinstance(pantry, list):
            return jsonify({"error": "pantry must be a list"}), 400
        if not pantry:
            return jsonify({"error": "pantry must be non-empty"}), 400
        if any(not isinstance(x, str) for x in pantry):
            return jsonify({"error": "pantry elements must be strings"}), 400
        if not isinstance(limit, int) or limit < 1:
            return jsonify({"error": "limit must be int >= 1"}), 400
        # Validate V1 parameters
        if not isinstance(allow_missing, int) or allow_missing < 0:
            return jsonify({"error": "allow_missing must be int >= 0"}), 400
        if not isinstance(diet_tags, list) or any(not isinstance(x, str) for x in diet_tags):
            return jsonify({"error": "diet_tags must be a list of strings"}), 400
        if max_cost is not None and not isinstance(max_cost, (int, float)):
            return jsonify({"error": "max_cost must be number >= 0 or null"}), 400
        if isinstance(max_cost, (int, float)) and max_cost < 0:
            return jsonify({"error": "max_cost must be number >= 0 or null"}), 400
        if not isinstance(use_substitutions, bool):
            return jsonify({"error": "use_substitutions must be bool"}), 400

        selected = plan_recipes(
            pantry,
            recipes,
            limit,
            allow_missing=allow_missing,
            diet_tags=diet_tags,
            max_cost=max_cost,
            use_substitutions=use_substitutions,
            substitutions=substitutions,
        )
        return jsonify({"recipes": selected})

    @app.get("/")
    def index():
        # Render empty form with defaults
        form = {
            "pantry": "",
            "limit": "",
            "allow_missing": "",
            "diet_tags": "",
            "max_cost": "",
            "use_substitutions": False,
        }
        return render_template("index.html", form=form, errors={}, recipes=None, submitted=False)

    @app.post("/")
    def index_post():
        # Parse form fields according to UI contracts
        form = {
            "pantry": request.form.get("pantry", ""),
            "limit": request.form.get("limit", ""),
            "allow_missing": request.form.get("allow_missing", ""),
            "diet_tags": request.form.get("diet_tags", ""),
            "max_cost": request.form.get("max_cost", ""),
            "use_substitutions": ("use_substitutions" in request.form),
        }

        errors = {}

        # pantry parsing
        raw = form["pantry"]
        tokens = []
        for line in raw.splitlines():
            for part in line.split(","):
                t = part.strip()
                if t:
                    tokens.append(t)
        if not tokens:
            errors["pantry"] = "pantry is required"

        # limit parsing: empty -> default 10; else int >=1, no decimals
        limit_val = 10
        if form["limit"].strip() != "":
            try:
                if "." in form["limit"]:
                    raise ValueError
                limit_val = int(form["limit"])
                if limit_val < 1:
                    raise ValueError
            except Exception:
                errors["limit"] = "limit must be int >= 1"

        # allow_missing: empty -> default 0; else int >=0, no decimals
        allow_missing_val = 0
        if form["allow_missing"].strip() != "":
            try:
                if "." in form["allow_missing"]:
                    raise ValueError
                allow_missing_val = int(form["allow_missing"])
                if allow_missing_val < 0:
                    raise ValueError
            except Exception:
                errors["allow_missing"] = "allow_missing must be int >= 0"

        # diet_tags: empty -> []; else split by commas, trim, drop empties (keep case)
        diet_tags_val = []
        if form["diet_tags"].strip() != "":
            diet_tags_val = [p.strip() for p in form["diet_tags"].split(",") if p.strip()]

        # max_cost: empty -> None; else float with dot; >=0
        max_cost_val = None
        if form["max_cost"].strip() != "":
            try:
                # only dot as decimal separator permitted
                if "," in form["max_cost"]:
                    raise ValueError
                max_cost_val = float(form["max_cost"])
                if max_cost_val < 0:
                    raise ValueError
            except Exception:
                errors["max_cost"] = "max_cost must be number >= 0 or empty"

        use_subs_val = bool(form["use_substitutions"])

        if errors:
            # Keep submitted=True but no recipes
            return render_template("index.html", form=form, errors=errors, recipes=None, submitted=True)

        # Call shared planner core; do not compute score/sorting/limit in UI
        selected = plan_recipes(
            tokens,
            recipes,
            limit_val,
            allow_missing=allow_missing_val,
            diet_tags=diet_tags_val,
            max_cost=max_cost_val,
            use_substitutions=use_subs_val,
            substitutions=substitutions,
        )
        return render_template("index.html", form=form, errors={}, recipes=selected, submitted=True)

    return app


if __name__ == "__main__":
    # Simple dev server
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
