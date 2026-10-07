# RoomBook — передача проекта

- Python, FastAPI, SQLite. Реализованы A (запрет пересечений, HTTP 409) и B (`GET /free-slots`).
- Интервалы `[start, end)`, рабочий день 09:00–18:00, шаг 30 минут.
- Перед работой прочитать `../AGENTS.md`, `PLAN.md` и `docs/style-guide.md`.

Команды из `room_booking_project`:

```sh
.venv/bin/python -m uvicorn app.api:app --reload
sh scripts/check.sh
```

Swagger: `http://127.0.0.1:8000/docs`. Проверка запускает pytest и Ruff.
База: `data/roombook.sqlite3` (путь можно задать через `ROOMBOOK_DB`); тесты используют временные базы.

OpenCode запускать из `practice_04`: там TDD skill, Context7 и hook проверки после редактирования Python.
Следующий этап — собственный skill `booking-csv-audit`: аудит CSV-заявок и конфликтов с расписанием, JSON/Markdown-отчёт без импорта. Требования — в `PLAN.md`.
