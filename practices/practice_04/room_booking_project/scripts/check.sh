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
        .venv/bin/python -m ruff check . ../.opencode/skills/booking-csv-audit/scripts --config ruff.toml
    else
        ruff check . ../.opencode/skills/booking-csv-audit/scripts --config ruff.toml
    fi
}

run_pytest "$@"
run_ruff
