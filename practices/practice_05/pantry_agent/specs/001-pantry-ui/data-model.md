# Data Model: pantry-ui

## Entities

### PantryInput
- Fields:
  - `pantry_lines`: list[str] — строки из textarea
  - `pantry_tokens`: list[str] — токены, полученные из строк и/или CSV

### UIForm
- Fields:
  - `pantry`: textarea (required)
  - `limit`: optional int (defaults 10 if empty)
  - `allow_missing`: optional int (defaults 0 if empty)
  - `diet_tags`: optional CSV string (defaults to [])
  - `max_cost`: optional number (absent if empty)
  - `use_substitutions`: optional bool (absent → false, present → true)

### PlanResult
- Fields:
  - `name`: str
  - `ingredients`: list[str]
  - `missing`: list[str]
  - `used_substitutions`: list[str]
  - `tags`: list[str]
  - `cost`: number
  - `score`: number

## Constraints
- Нормализация, допуски, сортировка и расчёт `score` выполняются в общем ядре; UI MUST NOT изменять порядок или значения
- `limit` применяется ядром последним; UI отображает результаты в полученном порядке
