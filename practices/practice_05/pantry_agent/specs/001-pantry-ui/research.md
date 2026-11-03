# Research: pantry-ui


  - Rationale: Соответствует конституции (Single Source of Truth), снижает риск расхождений
  - Alternatives considered: Дублировать логику в UI — отвергнуто (риск рассогласования)

  - Rationale: Простой UX, 200 на успех/валидацию, 500 на внутренние ошибки
  - Alternatives considered: Клиентский loader — не обязателен для серверного рендера

  - Rationale: Детализация UI→ядро для предсказуемости и тестов
  - Alternatives considered: Не фиксировать — отвергнуто

