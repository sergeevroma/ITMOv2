# Собственный MCP: RoomBook

Tool `find_free_slots(date, duration_minutes, room_id=None)` обращается к
`GET /free-slots` фичи B и возвращает `count` и `slots`. Только чтение.
Ошибки API превращаются в ошибку MCP tool с `isError: true`.
Python SDK формирует схему аргументов и обслуживает stdio; наша функция
связывает tool с API проекта и объясняет ошибки.

## Демо для пользователя

Все команды выполняются из `practices/practice_04`.
В первом терминале запусти API с временной базой:

```sh
room_booking_project/.venv/bin/python demo/demo_api.py
```

Во втором терминале открой новую сессию OpenCode. Подключение `roombook` уже
добавлено в `opencode.json`; отдельный процесс MCP запускает сам OpenCode.
Проверка подключения: `opencode mcp list`.

Промпт для успешного вызова:

> Вызови MCP tool roombook_find_free_slots: date="2099-10-12",
> duration_minutes=60, room_id=103. Покажи число интервалов и первые два.

Ожидаются 14 интервалов; первые два — 09:00–10:00 и 11:00–12:00.
Для демонстрации ошибки:

> Проверяем ошибочный вход MCP. Вызови roombook_find_free_slots с
> date="2099-10-12", duration_minutes=0, room_id=103.
> Не исправляй параметры заранее. Покажи ошибку инструмента.

Ожидается ошибка tool с HTTP 422 и указанием `duration_minutes`.

## Проверка без нейросети

```sh
room_booking_project/.venv/bin/python mcp/demo.py
```

Скрипт запускает настоящий MCP-процесс, выполняет initialize, tools/list
и два tools/call: успешный и ошибочный. Сравнивает все интервалы с HTTP API
и проверяет, что бронирования не изменились. В конце печатает PASS.
Зафиксированный результат: [demo-result.json](demo-result.json).

При другом адресе API используется `ROOMBOOK_API_URL` в MCP-конфигурации
и `--api-url` в демонстрационном клиенте.
Пример подключения без секретов: [opencode.example.json](opencode.example.json).
После переноса проекта пути к Python и server.py в конфигурации обновляются.

Основа: [MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/)
и [конфигурация MCP в OpenCode](https://opencode.ai/docs/mcp-servers/).
