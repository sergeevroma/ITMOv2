"""Проверить чувствительность браузерного теста, не меняя рабочий исходник."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main():
    environment = os.environ.copy()
    environment.setdefault(
        "PLAYWRIGHT_BROWSERS_PATH", str(PROJECT / ".venv" / "playwright-browsers")
    )
    with tempfile.TemporaryDirectory(prefix="roombook-mutation-") as directory:
        copy = Path(directory)
        for name in ("src", "tests"):
            shutil.copytree(
                PROJECT / name, copy / name, ignore=shutil.ignore_patterns("__pycache__")
            )
        shutil.copy2(PROJECT / "pyproject.toml", copy)
        client = copy / "src" / "front" / "app.js"
        source = client.read_text()
        original = "ui.formError.hidden = false;"
        assert source.count(original) == 1
        client.write_text(source.replace(original, "ui.formError.hidden = true;"))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/client/test_booking_flow.py",
                "-q",
                "--tb=short",
                "-k",
                "test_save_error_preserves_input_and_allows_retry and conflict",
            ],
            cwd=copy,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
    print("Контрольная поломка во временной копии: скрыто сообщение ошибки формы.")
    print(result.stdout, end="")
    print(result.stderr, end="")
    if result.returncode != 1 or "Locator expected to be visible" not in result.stdout:
        raise SystemExit("Контроль не подтверждён: ожидалось падение на видимости сообщения.")
    print("Ожидаемое падение подтверждено. Рабочий исходник не изменялся.")


if __name__ == "__main__":
    main()
