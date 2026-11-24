# Отчёт по практике 7.1: ассистент для код-ревью в n8n

## Окружение

- Репозиторий практики: [sergeevroma/N8N_practice](https://github.com/sergeevroma/N8N_practice).
- Первая модель: `openai/gpt-5`, провайдер VseLLM.
- Вторая модель: `anthropic/claude-sonnet-4.5`, провайдер VseLLM.
- Итоговый workflow: [two_agents_multifile.json](workflows/two_agents_multifile.json).

## 1. Классная работа: ревью только при открытии PR

**Статус:** подтверждено реальными запусками.

**Workflow:** [single_agent_without_command.json](workflows/single_agent_without_command.json).

**Что настроено:** GitHub Trigger получает события `pull_request`; IF пропускает только
`action = opened`. Две HTTP-ноды получают diff и README из коммита ветки PR.
Merge объединяет их в один элемент. Агент формирует ревью, GitHub-ноды публикуют его
и устанавливают метку `ReviewedByAI`.

**Тестовый PR:** [N8N_practice #1: bug-discount → main](https://github.com/sergeevroma/N8N_practice/pull/1).

**Результат ревью:** модель обнаружила ошибку в `shop.py`: выражение
`price * (1 + percent / 100)` увеличивает цену вместо применения скидки.
Для `price = 100`, `percent = 20` получается 120 вместо 80.
В опубликованном ревью предложено исправление: `price * (1 - percent / 100)`.
PR получил метку `ReviewedByAI`.

| Проверка | Ожидаемый результат | Фактический результат | Доказательство |
|---|---|---|---|
| Открыть новый PR | Опубликовано ревью, установлена метка | Execution №190 успешно выполнил всю цепочку; ревью и метка появились в PR | [Execution](screenshots/01_pr_opened/execution_opened.png), [результат в PR](screenshots/01_pr_opened/pr_review.png) |
| Закрыть PR без слияния | IF выбирает false, модель и публикация не выполняются | Execution №192 завершился после триггера и IF; HTTP-ноды, модель и публикация не выполнялись | [Execution](screenshots/01_pr_opened/execution_closed.png) |
| Повторно открыть PR | Событие reopened отсекается, нового ревью нет | Execution №193 завершился после триггера и IF; повторное ревью не выполнялось | [Execution](screenshots/01_pr_opened/execution_reopend.png) |

**Схема workflow:**

![Схема workflow](screenshots/01_pr_opened/workflow.png)

**Успешный запуск при открытии PR, Execution №190:**

![Ревью при открытии PR](screenshots/01_pr_opened/execution_opened.png)

**Опубликованное ревью и метка:**

![Ревью и метка в GitHub](screenshots/01_pr_opened/pr_review.png)

**Закрытие PR без слияния, Execution №192:**

![Закрытие PR отсекается](screenshots/01_pr_opened/execution_closed.png)

**Повторное открытие PR, Execution №193:**

![Повторное открытие PR отсекается](screenshots/01_pr_opened/execution_reopend.png)

## 2. Классная работа: ревью по команде /make_ai_review

**Статус:** подтверждено реальными запусками.

**Workflow:** [single_agent_with_command.json](workflows/single_agent_with_command.json).

**Что изменено:** GitHub Trigger переключён на событие `issue_comment`.
IF пропускает только новый комментарий (`action = created`), который относится к PR
и после удаления пробелов по краям совпадает с `/make_ai_review`.
Нода `Get PR details` получает сведения о PR для последующих запросов diff и README.
Открытие PR само по себе ревью не запускает.

**Тестовый PR:** [N8N_practice #2: bug-stock → main](https://github.com/sergeevroma/N8N_practice/pull/2).
Команда `/make_ai_review` и ответ модели показаны на [скриншоте обсуждения](screenshots/02_review_command/pr_review.png).

**Результат ревью:** модель обнаружила ошибку в `can_buy` файла `shop.py`:
условие `requested < stock` запрещает покупку всего остатка товара.
Для `stock = 5`, `requested = 5` функция возвращает `False` вместо `True`.
В ревью предложено восстановить `requested <= stock`; PR получил метку `ReviewedByAI`.

| Проверка | Ожидаемый результат | Фактический результат | Доказательство |
|---|---|---|---|
| Открыть PR | Автоматического ревью нет | После открытия PR ревью и метка отсутствовали | [PR до команды](screenshots/02_review_command/pr_before_command.png) |
| Написать обычный комментарий в PR | Модель и публикация не выполняются | Execution №194 завершился после триггера и IF; дальнейшие ноды не выполнялись | [Execution](screenshots/02_review_command/execution_ignored.png) |
| Написать /make_ai_review в PR | Основная модель публикует ревью | Execution №195 успешно выполнил всю цепочку; опубликовано ревью и установлена метка | [Execution](screenshots/02_review_command/execution_command.png), [результат в PR](screenshots/02_review_command/pr_review.png) |

**Схема workflow:**

![Схема запуска по команде](screenshots/02_review_command/workflow.png)

**PR после открытия, до отправки команды:**

![Автоматического ревью нет](screenshots/02_review_command/pr_before_command.png)

**Обычный комментарий, Execution №194:**

![Обычный комментарий отсекается](screenshots/02_review_command/execution_ignored.png)

**Запуск по /make_ai_review, Execution №195:**

![Успешное выполнение по команде](screenshots/02_review_command/execution_command.png)

**Команда, опубликованное ревью и метка:**

![Результат ревью по команде](screenshots/02_review_command/pr_review.png)

## 3. Домашняя работа: вторая модель

**Статус:** подтверждено опубликованными ревью и схемой workflow.

**Workflow:** [two_agents_with_command.json](workflows/two_agents_with_command.json).

**Что изменено:** IF принимает обе команды в новых комментариях к PR.
После получения diff и README нода Switch выбирает агента:
`/make_ai_review` направляется к GPT-5, а `/make_other_ai_review` — к Claude Sonnet 4.5.
GPT-5 использует общий промпт для ревью Python-кода; промпт Claude делает акцент
на требованиях README и граничных случаях, запрашивает минимальный пример ошибки,
исправление и короткий `assert`. Оба агента используют общие ноды публикации ревью
и установки метки `ReviewedByAI`. В заголовке нового ревью указывается модель.

**Тестовый PR:** [N8N_practice #2: bug-stock → main](https://github.com/sergeevroma/N8N_practice/pull/2).
Для сравнения используется тот же PR. Результат GPT-5 приведён в разделе 2;
его скриншот используется повторно. Для Claude добавлен отдельный скриншот ответа
на `/make_other_ai_review`.

| Команда | Использованная модель | Фактический результат | Доказательство |
|---|---|---|---|
| /make_ai_review | `openai/gpt-5` | Обнаружена ошибка `requested < stock`: при покупке всего остатка возвращается `False`; предложено восстановить `requested <= stock` | [Ревью GPT-5 из раздела 2](screenshots/02_review_command/pr_review.png) |
| /make_other_ai_review | `anthropic/claude-sonnet-4.5` | Опубликовано ревью с тем же дефектом, минимальным примером, исправлением и примерами `assert` для граничных случаев | [Ревью Claude](screenshots/03_second_model/pr_review_claude.png) |

**Сравнение результатов:** обе модели нашли один и тот же дефект в `shop.py`
и предложили одинаковое исправление: `return requested <= stock`.
Для `stock = 5`, `requested = 5` обе указали ожидаемый результат `True`
и фактический `False`. GPT-5 кратко описал нарушение требований и исправление.
Claude дополнительно предложил `assert` для равенства запроса и остатка,
запроса меньше и больше остатка, а также случая `stock = requested = 0`.

**Схема workflow с выбором агента:**

![Схема выбора модели по команде](screenshots/03_second_model/workflow.png)

**Ревью GPT-5 по /make_ai_review, скриншот из раздела 2:**

![Ревью GPT-5](screenshots/02_review_command/pr_review.png)

**Ревью Claude Sonnet 4.5 по /make_other_ai_review:**

![Ревью Claude Sonnet 4.5](screenshots/03_second_model/pr_review_claude.png)

## 4. Домашняя работа: сохранение состояния в Data Table

**Статус:** подтверждено опубликованным ревью и содержимым Data Table.

**Workflow:** [two_agents_with_db.json](workflows/two_agents_with_db.json).
Одна версия workflow реализует сохранение состояния и исключение повторного ревью.

**Таблица:** `reviewed_prs` в n8n.

| Поле | Тип | Назначение | Значение для тестового PR |
|---|---|---|---|
| `pr_id` | Number | Идентификатор PR из ответа GitHub API | `5265443284` |
| `pr_number` | Number | Номер PR в репозитории | `3` |
| `repository` | String | Полное имя репозитория | `sergeevroma/N8N_practice` |

Для поиска используется `pr_id`, полученный как `$("Get PR details").first().json.id`.
Он отличается от номера PR и служебного `id` строки таблицы.

**Когда сохраняется запись:** общая для обоих агентов нода `Save PR` стоит
после `GitHub Robot` и перед `Add Label to PR`. Она выполняет `Upsert` по `pr_id`:
создаёт запись либо обновляет существующую. Запись сохраняется после успешной
публикации ревью, независимо от выбранной модели.

**Тестовый PR:** [N8N_practice #3: bug-average → main](https://github.com/sergeevroma/N8N_practice/pull/3).
[Обсуждение с командами проверки](https://github.com/sergeevroma/N8N_practice/pull/3#issuecomment-6805170351).
В `average_rating` удалена обработка пустого списка. GPT-5 обнаружил, что
`average_rating([])` вызывает `ZeroDivisionError` вместо предусмотренного README
результата `0`, и предложил восстановить проверку `if not ratings: return 0`.
В PR опубликовано ревью и установлена метка `ReviewedByAI`.

| Проверка | Ожидаемый результат | Фактический результат | Доказательство |
|---|---|---|---|
| Выполнить ревью PR №3 | После публикации ревью его id сохранён в Data Table | GPT-5 опубликовал ревью; в `reviewed_prs` появилась строка с `pr_id = 5265443284`, `pr_number = 3` и именем репозитория | [Ревью и метка](screenshots/04_data_table/execution_saved.png), [Data Table](screenshots/04_data_table/table.png) |

**Схема workflow с проверкой и сохранением PR:**

![Workflow с Data Table](screenshots/04_data_table/workflow.png)

**Опубликованное ревью GPT-5 и метка:**

![Ревью PR №3 и метка](screenshots/04_data_table/execution_saved.png)

**Data Table после проверок: одна запись для PR №3:**

![Запись проверенного PR в reviewed_prs](screenshots/04_data_table/table.png)

## 5. Домашняя работа: исключение повторного ревью

**Статус:** подтверждено реальными запусками для обеих команд.

**Workflow:** [two_agents_with_db.json](workflows/two_agents_with_db.json).

**Как принимается решение:** после `Get PR details` общая нода `Check PR`
с операцией `If Row Does Not Exist` ищет `pr_id` в таблице `reviewed_prs`.
Если записи нет, она пропускает данные к получению diff и README, а затем
к выбору модели и публикации. Если запись найдена, нода не возвращает элементов,
и дальнейшие ноды не выполняются. Проверка применяется к `/make_ai_review`
и `/make_other_ai_review`: после ревью любой моделью повторное ревью этого PR
блокируется для обеих команд.

**Тестовый PR и команды:** [PR №3 и обсуждение проверки](https://github.com/sergeevroma/N8N_practice/pull/3#issuecomment-6805170351).
После первого `/make_ai_review` и сохранения записи последовательно отправлены
повторный `/make_ai_review` и `/make_other_ai_review`.

| Проверка | Ожидаемый результат | Фактический результат | Доказательство |
|---|---|---|---|
| /make_ai_review для PR, которого нет в таблице | Ревью опубликовано, id сохранён | Ревью GPT-5 опубликовано, в таблицу добавлена запись для PR №3 | [Ревью](screenshots/04_data_table/execution_saved.png), [Data Table](screenshots/04_data_table/table.png) |
| Повторный /make_ai_review для того же PR | Модель и публикация пропущены, дублирующая запись не создаётся | Выполнились только триггер, IF, получение сведений о PR и `Check PR`; последующие ноды не запускались | [Повторная основная команда](screenshots/05_deduplication/execution_skipped.png) |
| /make_other_ai_review для уже проверенного PR | Вторая модель и публикация также пропущены | Выполнение остановилось после `Check PR`; в Data Table осталась одна строка для PR №3 | [Команда второй модели](screenshots/05_deduplication/execution_other_skipped.png), [Data Table](screenshots/04_data_table/table.png) |

Каждый комментарий создаёт новый Execution, но для уже проверенного PR
не выполняются запросы diff и README, вызовы моделей, публикация ревью
и повторная запись в таблицу.

**Пропуск повторного /make_ai_review:**

![Основная команда останавливается на Check PR](screenshots/05_deduplication/execution_skipped.png)

**Пропуск /make_other_ai_review для того же PR:**

![Команда второй модели останавливается на Check PR](screenshots/05_deduplication/execution_other_skipped.png)

## 6. Домашняя работа со звёздочкой: точечные комментарии

**Статус:** подтверждено успешным Execution №208 и комментариями возле изменённых строк в GitHub.

**Workflow:** [two_agents_multifile.json](workflows/two_agents_multifile.json).

**Как разбивается diff:** после Merge нода Code `Split diff` разбирает текст diff.
По заголовкам файлов определяет путь, а по строкам `@@ … @@` выделяет отдельные
блоки изменений. При обходе строк ведёт счётчики старой и новой версий файла:
для `+` увеличивает номер новой строки, для `-` — старой, для контекста — оба.
Каждый блок получает ID (`h1`, `h2`), текст diff и координаты комментария.
README и массив блоков передаются одним item выбранному агенту.

**Ответ модели и публикация:** агент возвращает JSON с одним текстовым комментарием
на каждый `block_id`. Нода Code `Build Review` проверяет количество комментариев,
непустые тексты, отсутствие неизвестных и повторяющихся ID. Затем подставляет
координаты из разобранного diff. Путь и номер строки не генерируются моделью.
Нода HTTP Request `Publish inline review` отправляет один запрос
`POST /repos/{owner}/{repo}/pulls/{number}/reviews` с `event = COMMENT`
и массивом `comments`. После успешной публикации выполняются `Save PR`
и `Add Label to PR`.

| Поле запроса | Как определяется |
|---|---|
| `comments[].path` | Путь изменённого файла из diff |
| `comments[].line` | Номер первой добавленной строки блока; если добавлений нет — первой удалённой |
| `comments[].side` | `RIGHT` для добавленной строки, `LEFT` для удалённой |
| `commit_id` | SHA коммита ветки PR: `$("Get PR details").first().json.head.sha` |

**Тестовый PR:** [N8N_practice #4: bug-inline → main](https://github.com/sergeevroma/N8N_practice/pull/4).
В `shop.py` изменены две строки в разных блоках diff: формула скидки
и знаменатель при вычислении среднего рейтинга. Команда `/make_ai_review`
запустила GPT-5. Execution №208 завершился успешно за 18,052 секунды;
опубликовано одно ревью с двумя отдельными комментариями к коду.

| Проверка | Ожидаемый результат | Фактический результат | Доказательство |
|---|---|---|---|
| Блок с формулой скидки | Комментарий привязан к изменённой строке `discount_price` | Комментарий опубликован у `shop.py:6`, сторона `RIGHT`; GPT-5 обнаружил увеличение цены вместо скидки и предложил `price * (1 - percent / 100)` | [Ревью](screenshots/06_inline_comments/pr_inline_comments1.png), [Files changed](screenshots/06_inline_comments/pr_inline_comments2.png) |
| Блок с вычислением среднего рейтинга | Отдельный комментарий привязан к строке `average_rating` | Комментарий опубликован у `shop.py:16`, сторона `RIGHT`; обнаружено занижение среднего из-за `len(ratings) + 1`, предложено делить на `len(ratings)` | [Ревью](screenshots/06_inline_comments/pr_inline_comments1.png), [Files changed](screenshots/06_inline_comments/pr_inline_comments2.png) |

**Результат ревью:** оба изменённых блока получили свои комментарии.
Для второго дефекта модель привела пример: для `[5]` получается `2.5` вместо `5`.
В заголовке ревью указаны модель `openai/gpt-5` и число проверенных блоков — `2`.
На вкладке Files changed видны отдельные обсуждения у строк `R6` и `R16`.

**Итоговая схема workflow:**

![Workflow с точечными комментариями](screenshots/06_inline_comments/workflow.png)

**Успешный Execution №208:**

![Выполнение разбора diff и публикации inline-комментариев](screenshots/06_inline_comments/execution_inline.png)

**Команда и ревью с двумя комментариями:**

![Ревью GPT-5 по двум блокам изменений](screenshots/06_inline_comments/pr_inline_comments1.png)

**Привязка комментариев к строкам во вкладке Files changed:**

![Комментарии у строк R6 и R16](screenshots/06_inline_comments/pr_inline_comments2.png)

## Итог сдачи

- [x] Добавлены ссылки на выполненные версии workflow и выбран финальный JSON.
- [x] Добавлены ссылки на тестовые PR и результаты ревью.
- [x] Приложены схемы workflow и результаты ревью; для проверок запуска и пропуска — реальные Executions.
- [x] Для сохранения состояния и дедупликации показано содержимое Data Table.
- [x] Пояснены выбор модели, хранение состояния и пропуск повторного ревью.
- [x] Для выполненной звёздочки показана привязка комментариев к блокам кода.

**Выполненные этапы и ограничения:** выполнены оба этапа классной работы
и все четыре шага домашней работы: вторая модель, сохранение PR в Data Table,
исключение повторного ревью и точечные комментарии к блокам изменений.
Публикация точечных комментариев подтверждена запуском GPT-5 на двух блоках
одного файла; выбор второй модели сохранён в итоговой схеме.
Дедупликация действует по идентификатору PR для обеих команд; последовательные
повторные вызовы подтверждены скриншотами. Защита от одновременных запусков
до сохранения первой записи не реализована.
