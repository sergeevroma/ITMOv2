# Tasks: pantry-ui

**Input**: Design documents from `/specs/001-pantry-ui/`

**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

## Path Conventions
- Single project: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 [P] Создать каталог шаблонов UI: `src/templates/` (без изменения кода)
- [ ] T002 [P] Создать каталоги тестов: `tests/ui/` и `tests/api/`
- [ ] T003 [P] Добавить пустые файлы-стабы тестов для последующего наполнения

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T010 Зафиксировать единый вызов ядра планирования/валидации (использовать существующий `planner.py` и общий метод; код не менять на этом этапе)
- [ ] T011 Подготовить фикстуры Flask test client (API и UI) в `tests/conftest.py`
- [ ] T012 Подготовить/проверить тестовые данные с тегами/стоимостью/заменами (`src/data/recipes.json`, `src/data/substitutions.json` если есть)

---

## Phase 3: User Story 1 — Ввод pantry и получение планов (P1)

### Tests (сначала)
- [ ] T101 [US1] API: 200 на валидный pantry, сортировка по имени (V0) — `tests/api/test_plan_v0.py`
- [ ] T102 [US1] UI: POST `/` с pantry, сохранение значений, совпадение порядка с API — `tests/ui/test_ui_v0.py`

### Implementation (после тестов)
- [ ] T103 [US1] Подготовить шаблон `src/templates/index.html` (форма + блок результатов), без логики вычислений

---

## Phase 4: User Story 2 — Ошибки валидации полей (P1)

### Tests
- [ ] T201 [US2] UI: пустой pantry → 200, сообщение у поля, сохранение значений — `tests/ui/test_ui_errors.py`
- [ ] T202 [US2] UI: `limit="0"`, `allow_missing="-1"`, `max_cost="-1"` → 200, сообщения у полей — `tests/ui/test_ui_errors.py`

---

## Phase 5: User Story 3 — Нет совпадений (P2)

### Tests
- [ ] T301 [US3] UI: валидный pantry без совпадений → 200, сообщение о пустом результате — `tests/ui/test_ui_empty.py`

---

## Parity Tests (UI ↔ API)

- [ ] T401 [P] allow_missing>0: UI и API дают идентичные рецепты и порядок — `tests/ui/test_parity_allow_missing.py`
- [ ] T402 [P] diet_tags AND: идентичный набор и порядок — `tests/ui/test_parity_tags.py`
- [ ] T403 [P] max_cost: порог и влияние на `score` — `tests/ui/test_parity_cost.py`
- [ ] T404 [P] use_substitutions=true: одношаговая замена — `tests/ui/test_parity_substitutions.py`
- [ ] T405 [P] Пустой результат: идентичный пустой список — `tests/ui/test_parity_empty.py`

---

## Contracts Alignment

- [ ] T501 Сверить `contracts/ui-form-contract.md` с тестами формы
- [ ] T502 Сверить `contracts/api-contract.md` с API тестами
- [ ] T503 Сверить `contracts/parity-tests.md` с тестами паритета

---

## Notes
- Код приложения пока не менять; задачи формируют дорожную карту разработки и тестирования.
