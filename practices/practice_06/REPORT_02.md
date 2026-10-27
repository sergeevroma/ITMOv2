# Отчёт 2. Повторные атаки после исправлений

Источник уязвимостей и исправлений: REPORT_01.md, изменения в lab/service.py, регрессионные тесты в lab/test_security_regressions.py.
Доказательства повторных проверок собраны в lab/evidence/after/ скриптом lab/attacks_after.py.

Формат ниже: ID → исправление → повторный запрос → ожидаемый и фактический результат → доказательство.

- S-01 Подмена сотрудника (GET /admin/export)
  Исправление: требование сессии и проверка роли staff по токену; игнорирование заголовка X-Role без сессии.
  Повторный запрос: 
  - Гость: GET /admin/export c X-Role: staff
  - Клиент: GET /admin/export с X-Token (alice)
  - Сотрудник: GET /admin/export с X-Token (staff)
  Ожидание: 401 гостю; 403 клиенту; 200 сотруднику.
  Факт: совпало. Доказательства: 
  - lab/evidence/after/S-01_guest_admin_export_spoof_*.txt
  - lab/evidence/after/S-01_alice_admin_export_customer_*.txt
  - lab/evidence/after/S-01_staff_admin_export_ok_*.txt

- I-01 Открытые логи (GET /debug/logs)
  Исправление: доступ только staff по сессии; маскировка пароля и удаление X-Token; лимит 500 записей.
  Повторный запрос: 
  - Гость: GET /debug/logs
  - Сотрудник: GET /debug/logs с X-Token (staff)
  Ожидание: 401 гостю; 200 staff; в теле нет открытого пароля и X-Token.
  Факт: совпало (пароль заменён на ***; X-Token отсутствует). Доказательства:
  - lab/evidence/after/I-01_guest_debug_logs_guest_*.txt
  - lab/evidence/after/I-01_staff_debug_logs_staff_*.txt

- S-02 Использование украденного токена
  Исправление: основной вектор закрыт за счёт защиты логов; токен остается bearer-кредитивом.
  Повторный запрос: POST /orders с X-Token (alice) от «атакера».
  Ожидание: 201, заказ создаётся, так как токен действителен; риск снижен благодаря I-01.
  Факт: совпало. Доказательство: lab/evidence/after/S-02_attacker_with_stolen_token_create_order_*.txt

- T-01 Подмена цены при заказе
  Исправление: цена берётся только с сервера из каталога.
  Повторный запрос: POST /orders {product: lamp, price: 1} с X-Token (alice).
  Ожидание: 201, price=1500.
  Факт: совпало. Доказательство: lab/evidence/after/T-01_alice_price_override_*.txt

- I-02 Чтение чужих профилей
  Исправление: /profile требует сессию; клиент может читать только свой id; staff — любой.
  Повторный запрос: 
  - Гость: GET /profile?id=2
  - Alice: GET /profile?id=2
  Ожидание: 401 гостю; 403 Alice.
  Факт: совпало. Доказательства: lab/evidence/after/I-02_guest_profile_guest_*.txt, lab/evidence/after/I-02_alice_profile_foreign_*.txt

- I-03 Чтение всех заказов
  Исправление: /orders требует сессию; клиенту — только собственные, staff — все.
  Повторный запрос: 
  - Гость: GET /orders
  - Alice: GET /orders
  Ожидание: 401 гостю; 200 Alice только с owner=1.
  Факт: совпало. Доказательства: lab/evidence/after/I-03_guest_orders_guest_*.txt, lab/evidence/after/I-03_alice_orders_alice_*.txt

- I-04 Доступ к служебным файлам через /files
  Исправление: /files требует сессию; клиент может читать только files/<своё_имя>/...; запрет «..» в path.
  Повторный запрос: 
  - Гость: GET /files?user=alice&path=receipt.txt
  - Alice: GET /files?user=alice&path=../private/operator-note.txt
  Ожидание: 401 гостю; 403 при попытке обхода.
  Факт: совпало. Доказательства: lab/evidence/after/I-04_guest_files_guest_*.txt, lab/evidence/after/I-04_alice_files_traversal_private_*.txt

- I-05 SQL-инъекция в /profile
  Исправление: параметризованный запрос и проверка id как int.
  Повторный запрос: GET /profile?id=1 OR 1=1-- с X-Token (alice).
  Ожидание: 400 invalid id.
  Факт: совпало. Доказательство: lab/evidence/after/I-05_alice_sql_injection_profile_*.txt

- E-01 Политика /assistant/execute
  Исправление: требование сессии; мандат по инструментам (export — staff; read_file — только files/ и своё поддерево; delete_tree — только staff и внутри files/).
  Повторный запрос: 
  - Гость: POST /assistant/execute {tool: export_profiles}
  - Alice: POST /assistant/execute {tool: export_profiles}
  - Alice: POST /assistant/execute {tool: read_file, path: private/...}
  - Alice: POST /assistant/execute {tool: read_file, path: files/alice/receipt.txt}
  Ожидание: 401; 403; 403; 200 соответственно.
  Факт: совпало. Доказательства: lab/evidence/after/E-01_guest_assistant_execute_export_*.txt, lab/evidence/after/E-01_alice_assistant_execute_export_*.txt, lab/evidence/after/E-01_alice_assistant_execute_read_private_*.txt, lab/evidence/after/E-01_alice_assistant_execute_read_own_*.txt

- I-06 Контекст ассистента
  Исправление: /assistant/context требует сессию; проверяется владение заказом (кроме staff).
  Повторный запрос: 
  - Гость: GET /assistant/context?order_id=2
  - Alice: GET /assistant/context?order_id=2
  - Alice: GET /assistant/context?order_id=1
  Ожидание: 401; 403; 200.
  Факт: совпало. Доказательства: lab/evidence/after/I-06_guest_assistant_context_order2_*.txt, lab/evidence/after/I-06_alice_assistant_context_order2_*.txt, lab/evidence/after/I-06_alice_assistant_context_order1_*.txt

- I-07/E-02 Stored XSS в /reviews/view
  Исправление: обязательная аутентификация при POST /reviews; HTML-экранирование при /reviews/view; ограничение до 100 записей.
  Повторный запрос: 
  - Alice: POST /reviews с текстом <script>...
  - Alice: GET /reviews/view
  Ожидание: 201; 200 и нет сырого <script>, отображается как текст.
  Факт: совпало, в выдаче присутствуют экранированные символы. Доказательства: lab/evidence/after/I-07_E-02_alice_reviews_submit_script_*.txt, lab/evidence/after/I-07_E-02_alice_reviews_view_*.txt

- P-01 Prompt-инъекция в контексте ассистента
  Исправление: на уровне исполнения — строгая политика в /assistant/execute. Контекст по-прежнему включает пользовательские отзывы и должен рассматриваться как недоверенный ввод для модели.
  Повторный запрос: Alice: GET /assistant/context?order_id=1 после отправки инструкции в отзыве.
  Ожидание: инструкция в prompt присутствует, но попытки нарушить политику через /assistant/execute блокируются.
  Факт: совпало. Доказательство: lab/evidence/after/P-01_alice_assistant_context_contains_instructions_*.txt

Оставшиеся ограничения

- Токен сессии — обычный bearer-токен. Если он скомпрометирован и не отозван, злоумышленник может действовать от имени пользователя в пределах его ролей. Основная защита — недоступность токенов из логов и ограничение областей применения.
- Контекст ассистента содержит пользовательские данные (включая отзывы), которые могут содержать инструкции; защита обеспечивается исключительно политикой исполнения на сервере, фильтрация prompt не производится.
- Диагностический журнал отдаётся staff без строжайшей маскировки всех полей: пароль скрывается, X-Token исключается; остальные заголовки и тела остаются в рамках здравого смысла (без PII маскирования помимо вышеописанного).
- Упрощённая модель пользователей/ролей и отсутствие TTL/ротации токенов — сознательное упрощение упражнения.
