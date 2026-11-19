"""Сохранить контракт API или проверить, что сохранённая версия актуальна."""

import argparse
import json
from pathlib import Path

from roombook.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Только проверить актуальность")
    arguments = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    schema = create_app().openapi()
    if arguments.check:
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != schema:
            raise SystemExit("OpenAPI изменился. Запустите scripts/export_openapi.py без --check.")
        print("OpenAPI: актуален")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"OpenAPI: {path}")


if __name__ == "__main__":
    main()
