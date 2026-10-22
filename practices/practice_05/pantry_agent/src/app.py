from __future__ import annotations

from flask import Flask, jsonify, request

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

    return app


if __name__ == "__main__":
    # Simple dev server
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
