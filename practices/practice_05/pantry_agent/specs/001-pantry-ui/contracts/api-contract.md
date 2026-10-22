# JSON API Contract (Reference for UI)

## Endpoint
- `POST /v1/plan`

## Request Body (V1)
- `pantry`: list[str] (required, non-empty)
- `limit`: int ≥ 1 (optional, default 10)
- `allow_missing`: int ≥ 0 (optional, default 0)
- `diet_tags`: list[str] (optional, default [])
- `max_cost`: number ≥ 0 (optional, absent if not set)
- `use_substitutions`: bool (optional, default false)

## Response 200
- `recipes`: list of objects with fields:
  - `name`: str
  - `ingredients`: list[str]
  - `missing`: list[str] (normalized)
  - `used_substitutions`: list[str] (e.g., "scallion<-green onion")
  - `tags`: list[str]
  - `cost`: number
  - `score`: number (rounded to 3 decimals)

## Response 400 (validation errors)
- JSON с деталями по полям (текст сообщений — по реализации)

## Response 500 (internal error)
- Обобщённая ошибка сервера
