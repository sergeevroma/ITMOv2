# Демо booking-csv-audit: инструкция для пользователя

Этот файл описывает подготовку сервера и проверку демо пользователем.
Работа агента описана в [SKILL.md](../SKILL.md).

Все команды ниже выполняются из `practices/practice_04`.
CSV имеет пять колонок `room_id,title,date,start,end`, UTF-8, разделитель — запятая.
Номер записи в отчёте начинается с 2; кавычки позволяют использовать запятую в названии.

## Обычный аудит

```sh
room_booking_project/.venv/bin/python .opencode/skills/booking-csv-audit/scripts/audit_csv.py \
  --csv .opencode/skills/booking-csv-audit/examples/issues.csv \
  --api-url http://127.0.0.1:8765 \
  --output-dir room_booking_project/reports/booking-csv-audit
```

Адрес демо-API по умолчанию — `http://127.0.0.1:8765`.
Для обычного RoomBook на порту 8000 адрес передаётся явно через `--api-url`.
Скрипт создаёт `<имя-CSV>.json` и `<имя-CSV>.md` и печатает пути к ним.
Коды завершения: 0 — `clean`, 1 — `issues_found`, 2 — `failed`.
Код 1 означает найденные ошибки заявок, а не сбой программы.

## Воспроизводимое демо

Чтобы не запускать реальный сервер и базу данных, используется demo_api:

```sh
room_booking_project/.venv/bin/python .opencode/skills/booking-csv-audit/scripts/demo_api.py
```

Сервер на порту 8765 использует временную базу.
В ней только бронирование из [schedule.json](../examples/schedule.json)
Пользовательская база не затрагивается; Ctrl+C останавливает сервер.

Во втором терминале открывается OpenCode из `practice_04`:

```text
Загрузи booking-csv-audit через инструмент skill.
Проверь .opencode/skills/booking-csv-audit/examples/issues.csv.
API: http://127.0.0.1:8765.
Каталог отчётов: room_booking_project/reports/booking-csv-audit.
Запусти скрипт пакета, покажи сводку и пути к отчётам.
Файлы кода и CSV не изменяй, бронирования не создавай.
```

Повторяется для `clean.csv` и `schedule-conflict.csv`.

| CSV | Ожидаемый результат |
|---|---|
| clean | `clean`: 3 заявки, ошибок и конфликтов нет |
| issues | `issues_found`: неверные записи 4 и 5, конфликт записей 2 и 3 |
| schedule-conflict | `issues_found`: запись 2 конфликтует с бронированием ID 1 |

Ожидания заданы вручную в `examples/expected.json`.
После трёх запусков сравни реальные JSON-отчёты:

```sh
room_booking_project/.venv/bin/python .opencode/skills/booking-csv-audit/scripts/verify_reports.py \
  --output-dir room_booking_project/reports/booking-csv-audit
```

Ожидается три строки `PASS`. Просмотри также таблицы в Markdown-отчётах.
Для проверки недоступного API повтори аудит с `--api-url http://127.0.0.1:1`:
ожидается `failed`, код 2 и описание ошибки, а не утверждение о свободном расписании.
