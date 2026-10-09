"""Compare generated demo reports with manually specified expectations."""

import argparse
import json
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


def projection(report):
    return {
        "status": report["status"],
        "summary": report["summary"],
        "invalid_rows": [row["row"] for row in report["invalid_rows"]],
        "conflicts": report["conflicts"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads((SKILL_DIR / "examples" / "expected.json").read_text())
    for name, wanted in expected.items():
        path = args.output_dir / f"{name}.json"
        actual = json.loads(path.read_text())
        if projection(actual) != wanted or actual["errors"]:
            raise SystemExit(f"FAIL: {name}: {actual}")
        if not path.with_suffix(".md").is_file():
            raise SystemExit(f"FAIL: отсутствует Markdown для {name}")
        print(f'PASS: {name}: {actual["status"]}')


if __name__ == "__main__":
    main()
