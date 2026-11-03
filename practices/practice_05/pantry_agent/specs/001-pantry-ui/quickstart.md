# Quickstart: pantry-ui

## Предпосылки
- Тесты: `PYTHONPATH=src .venv/bin/python -m pytest -q`

## Проверка API V1
- POST `/v1/plan` JSON:
  ```json
  {"pantry":["egg","milk","salt"],"limit":5}
  ```
- Ожидаем: 200; сортировка по имени; непустой `recipes` (зависит от данных)

## Проверка UI
- GET `/` — форма отображается
- POST `/` форма:
  - `pantry`: `egg, milk, salt`
  - `limit`: пусто (default 10)
  - остальные поля пусты
- Ожидаем: 200; та же страница с результатами; порядок совпадает с API

## Parity Check
- Повторить входы через API и UI для кейсов:
  - `allow_missing=1`
  - `diet_tags=vegetarian,breakfast`
  - `max_cost=5.5`
  - `use_substitutions` отмечен
- Ожидаем: одинаковые рецепты и порядок

## Ошибки валидации
- `pantry`: пусто → 200 + сообщение у поля
- `limit="0"` → 200 + сообщение у поля limit
- `max_cost="-1"` → 200 + сообщение у поля max_cost

## Внутренние ошибки
- Симуляция внутренней ошибки → 500, простая страница ошибки
