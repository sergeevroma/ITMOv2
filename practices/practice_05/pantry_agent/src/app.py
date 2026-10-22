from __future__ import annotations

from flask import Flask, jsonify, request

from planner import plan_recipes, load_recipes


def create_app() -> Flask:
    app = Flask(__name__)

    # Load data once at startup
    recipes = load_recipes()

    @app.route("/v1/plan", methods=["POST"])
    def plan():
        # Validate JSON body
        if not request.is_json:
            return jsonify({"error": "expected application/json"}), 400
        payload = request.get_json()

        pantry = payload.get("pantry")
        limit = payload.get("limit", 10)

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

        selected = plan_recipes(pantry, recipes, limit)
        return jsonify({"recipes": selected})

    return app


if __name__ == "__main__":
    # Simple dev server
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
