#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

ROOMBOOK_PYTHON="${ROOMBOOK_PYTHON:-.venv/bin/python}"
"$ROOMBOOK_PYTHON" -m ruff check .
"$ROOMBOOK_PYTHON" -m ruff format --check .
"$ROOMBOOK_PYTHON" scripts/export_openapi.py --check
"$ROOMBOOK_PYTHON" -m pytest -q

