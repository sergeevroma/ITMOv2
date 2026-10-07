#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

run_pytest() {
    if [ -x .venv/bin/python ]; then
        .venv/bin/python -m pytest -q "$@"
    else
        python3 -m pytest -q "$@"
    fi
}

run_ruff() {
    if [ -x .venv/bin/python ]; then
        .venv/bin/python -m ruff check .
    else
        ruff check .
    fi
}

run_pytest "$@"
run_ruff
