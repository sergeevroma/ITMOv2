"""Read-only CSV audit against the RoomBook API."""

import argparse
import csv
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import ValidationError

PROJECT_DIR = Path(__file__).resolve().parents[4] / "room_booking_project"
FIELDS = ["room_id", "title", "date", "start", "end"]


class AuditError(Exception):
    """Input or API failure that prevents a complete audit."""


def booking_models():
    sys.path.insert(0, str(PROJECT_DIR))
    from app.models import Booking, BookingInput

    return Booking, BookingInput


def read_rows(path):
    _, booking_input = booking_models()
    valid, invalid = [], []
    total = 0
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if (
                not reader.fieldnames
                or len(reader.fieldnames) != len(FIELDS)
                or set(reader.fieldnames) != set(FIELDS)
            ):
                raise AuditError("CSV должен содержать колонки: " + ",".join(FIELDS))
            for number, raw in enumerate(reader, start=2):
                total += 1
                if None in raw or any(value is None for value in raw.values()):
                    invalid.append({"row": number, "errors": ["Неверное число полей"]})
                    continue
                try:
                    raw["room_id"] = int(raw["room_id"])
                    item = booking_input.model_validate(raw).model_dump(mode="json")
                    valid.append({"row": number, "booking": item})
                except ValueError as error:
                    if isinstance(error, ValidationError):
                        reasons = [
                            f'{".".join(map(str, e["loc"])) or "interval"}: {e["msg"]}'
                            for e in error.errors()
                        ]
                    else:
                        reasons = ["room_id должен быть целым числом"]
                    invalid.append({"row": number, "errors": reasons})
    except (OSError, UnicodeError, csv.Error) as error:
        raise AuditError(f"Не удалось прочитать CSV: {error}") from error
    return total, valid, invalid


def fetch_bookings(api_url, day):
    booking_model, _ = booking_models()
    url = api_url.rstrip("/") + "/bookings?" + urlencode({"date": day})
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise AuditError(f"API вернул HTTP {response.status}")
            payload = json.loads(response.read())
    except (HTTPError, URLError, OSError, ValueError) as error:
        raise AuditError(f"Не удалось получить расписание {day}: {error}") from error
    if not isinstance(payload, list):
        raise AuditError("API должен вернуть список бронирований")
    result = []
    for item in payload:
        if (
            not isinstance(item, dict)
            or type(item.get("id")) is not int
            or item["id"] <= 0
        ):
            raise AuditError("В ответе API отсутствует корректный ID бронирования")
        try:
            booking = booking_model.model_validate(item).model_dump(mode="json")
        except ValidationError as error:
            raise AuditError("В ответе API некорректные поля бронирования") from error
        if booking["date"] != day:
            raise AuditError("API вернул бронирование другой даты")
        result.append(booking)
    return result


def overlaps(first, second):
    return (
        first["room_id"] == second["room_id"]
        and first["date"] == second["date"]
        and first["start"] < second["end"]
        and second["start"] < first["end"]
    )


def audit_csv(csv_path, api_url):
    report = {
        "status": "clean",
        "summary": {"total_rows": 0, "invalid_rows": 0, "conflicting_rows": 0},
        "invalid_rows": [],
        "conflicts": [],
        "errors": [],
    }
    try:
        total, rows, invalid = read_rows(Path(csv_path))
        report["summary"].update(total_rows=total, invalid_rows=len(invalid))
        report["invalid_rows"] = invalid
        for index, first in enumerate(rows):
            for second in rows[index + 1:]:
                if overlaps(first["booking"], second["booking"]):
                    for current, other in [(first, second), (second, first)]:
                        report["conflicts"].append({
                            "row": current["row"],
                            "source": "csv",
                            "other_row": other["row"],
                        })
        schedule = {
            day: fetch_bookings(api_url, day)
            for day in sorted({row["booking"]["date"] for row in rows})
        }
        for row in rows:
            for booking in schedule[row["booking"]["date"]]:
                if overlaps(row["booking"], booking):
                    report["conflicts"].append({
                        "row": row["row"],
                        "source": "schedule",
                        "booking_id": booking["id"],
                    })
        if invalid or report["conflicts"]:
            report["status"] = "issues_found"
    except AuditError as error:
        report["status"] = "failed"
        report["errors"].append(str(error))
    report["conflicts"].sort(key=lambda c: (
        c["row"], c["source"], c.get("other_row", c.get("booking_id", 0))
    ))
    report["summary"]["conflicting_rows"] = len({
        conflict["row"] for conflict in report["conflicts"]
    })
    return report


def markdown(report):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    summary = report["summary"]
    lines = [
        "# Аудит CSV-заявок", "", f'Статус: **{report["status"]}**', "",
        f'Заявок: {summary["total_rows"]}; невалидных: {summary["invalid_rows"]}; '
        f'с конфликтами: {summary["conflicting_rows"]}.', "",
        "## Ошибки данных", "", "| Запись | Причина |", "|---|---|",
    ]
    for row in report["invalid_rows"]:
        lines.append(f'| {row["row"]} | {cell("; ".join(row["errors"]))} |')
    lines.extend([
        "", "## Конфликты", "", "| Запись | Источник | Конфликт с |", "|---|---|---|",
    ])
    for conflict in report["conflicts"]:
        partner = (
            f'запись {conflict["other_row"]}' if conflict["source"] == "csv"
            else f'бронирование ID {conflict["booking_id"]}'
        )
        lines.append(f'| {conflict["row"]} | {conflict["source"]} | {partner} |')
    if report["errors"]:
        lines.extend(["", "## Проверка не завершена", ""])
        lines.extend(f"- {cell(error)}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--output-dir", type=Path,
        default=PROJECT_DIR / "reports" / "booking-csv-audit",
    )
    args = parser.parse_args(argv)
    report = audit_csv(args.csv, args.api_url)
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = args.output_dir / f"{args.csv.stem}.json"
        md_path = args.output_dir / f"{args.csv.stem}.md"
        json_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        md_path.write_text(markdown(report), encoding="utf-8")
    except OSError as error:
        print(f"failed: не удалось сохранить отчёты: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["status"], "summary": report["summary"],
        "json": str(json_path), "markdown": str(md_path),
    }, ensure_ascii=False))
    return {"clean": 0, "issues_found": 1, "failed": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
