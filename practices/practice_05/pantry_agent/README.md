# Pantry Planner Agent (V0)

Цель: по списку ингредиентов (pantry) вернуть рецепты, которые можно приготовить без докупки.

Стек
- Python 3.10+
- Flask (минимальный backend)
- pytest

Запуск
1. Установка зависимостей:
   pip install flask pytest
   или
   pip install -e .
2. Запуск сервера разработки:
   PYTHONPATH=src python -m app
3. Вызов API:
   POST http://localhost:5000/v1/plan
   Тело:
   {
     "pantry": ["egg", "milk", "salt"],
     "limit": 5
   }

Тесты
- Запуск: PYTHONPATH=src pytest

Спецификация V0
- См. AGENTS.md для деталей API, данных и алгоритма.

План расширений
- V1: allow_missing, теги, стоимость, замены, ранжирование.
- V2: UI (Flask + Jinja2).
