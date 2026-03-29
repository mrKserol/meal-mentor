# Meal Mentor

Трекер калорий и состава еды по фото: FastAPI-бэкенд, Telegram-бот и Streamlit для демо/админки.

## Структура проекта

```
meal-mentor/
├── app/
│   ├── core/              # Схемы данных, use cases (анализ приёма пищи без Telegram)
│   ├── infrastructure/    # OpenAI (vision/text), nutrition.csv provider
│   ├── interfaces/        # Слой интерфейсов: FastAPI (api/), Telegram (telegram/), заготовка MAX
│   ├── api/               # Шимы для старых импортов → interfaces.api
│   ├── bot/               # Шимы → interfaces.telegram (точка входа бота без изменений)
│   ├── db/                # Модели, сессия, репозиторий
│   ├── services/          # meal_service (фасад), отчёты, рекомендации; шимы openai/nutrition
│   └── main.py            # FastAPI-приложение
├── docs/
│   ├── architecture.md           # Как устроены core / interfaces / flow
│   ├── architecture_audit.md     # Аудит до/после рефакторинга
│   └── refactor_next_steps.md    # Следующие этапы (без реализации)
├── alembic/               # Миграции схемы БД
├── data/
│   ├── nutrition.csv
│   └── promt.txt, promt2.txt
├── service.py             # Точка входа для uvicorn service:app
├── ui.py                  # Streamlit (демо), клиент к API
├── requirements.txt
└── README.md
```

Подробнее: [docs/architecture.md](docs/architecture.md).

## Как работает

- **Telegram:** фото → `POST /meals/analyze` (без записи в БД) → ответ с составом и БЖУ → пользователь подтверждает «Да» → `POST /meals/save`. Если пустой результат или низкая уверенность — бот просит **текстовое описание** → `POST /meals/analyze-text` → снова подтверждение. Состояние диалога хранится в памяти процесса бота (`USER_STATES`); при нескольких репликах бота нужен общий store (Redis). `/report [дней]` — сводка (суммы по `MealItemNutrition`).
- **Ядро:** сценарий анализа сосредоточен в `app/core/use_cases/meal_analysis.py` (без типов Telegram).
- **Streamlit (ui.py):** демо/админ: загрузка фото → запрос к `POST /generate_response` → вывод состава, веса и при наличии CSV — диаграмма БЖУ.

## Переменные окружения

- `OPENAI_API_KEY` — ключ OpenAI (обязательно для vision).
- `PROMPT_PATH` — промпт для анализа **фото** (по умолчанию `./data/promt.txt`).
- `PROMPT2_PATH` — промпт для анализа **текста** (по умолчанию `./data/promt2.txt`).
- `LOW_CONFIDENCE_THRESHOLD` — порог уверенности 0–1; ниже — бот просит описать еду текстом (по умолчанию `0.5`).
- `NUTRITION_CSV_PATH` — путь к CSV с нутриентами на 100 г (по умолчанию `./data/nutrition.csv`, колонки: `name`, `calories`, `total_fat`, `protein`, `carbohydrate`). Необязательно.
- `NUTRITION_ENABLE_SEMANTIC` — если `true`, при семантическом поиске ингредиентов подгружается модель с Hugging Face (на Railway часто таймаут). По умолчанию **выключено**; для расчёта БЖУ достаточно **fuzzy**-поиска по CSV.
- `TELEGRAM_BOT_TOKEN` — токен бота (для запуска бота).
- `BASE_URL` — URL бэкенда (по умолчанию `http://127.0.0.1:8000`). Нужен боту для вызова API.
- `DATABASE_URL` — БД (по умолчанию `sqlite:///./meal_mentor.db`).

## Запуск

1. Установка: `pip install -r requirements.txt`
2. Бэкенд: `uvicorn service:app --reload`
3. Telegram-бот: `python -m app.bot.telegram_bot` (предварительно запустить бэкенд)
4. Streamlit (демо): `streamlit run ui.py`

Можно по-прежнему использовать `make run_app` (бэкенд + Streamlit).

## Схема БД

Нормализованные таблицы: `users` (профиль), `meals`, `meal_items`, `meal_item_nutrition`, `daily_summary`, `recommendations_log`, `user_measurements`. JSON-поля для состава и нутриентов удалены.

## Миграции (Alembic)

Для существующей БД со старыми таблицами `meal_logs` / `users` (без колонки `first_name` у пользователя):

```bash
alembic upgrade head
```

Ревизия `001_normalize` удаляет `meal_logs`, при необходимости удаляет устаревшую таблицу `users` и создаёт новую схему через `Base.metadata.create_all`. **Данные в старых таблицах при этом теряются**, если вы явно не сделали бэкап.

На пустой БД достаточно `init_db()` при старте приложения или той же команды `alembic upgrade head`.

## API

- `POST /generate_response` — тело `{ "image_base64": "..." }` — состав и вес, при наличии CSV — поле `nutrition` (для ui.py).
- `POST /meals/analyze` — то же по полю `image_base64`.
- `POST /meals/analyze-text` — тело `{ "text": "..." }` — разбор описания блюда (без записи в БД).
- `POST /meals/save` — тело `{ "telegram_id", "ingredients": { ... }, "source_type", "username?", "first_name?", "telegram_file_id?" }` — запись подтверждённого приёма пищи.
- `POST /meals/log` — устаревший сценарий «анализ фото + сразу запись» в один запрос.
- `POST /users/register` — регистрация / обновление профиля: `telegram_id`, `username`, опционально `first_name`, `sex`, `birth_date`, `height_cm`, `weight_kg`, `goal`, `activity_level`, `timezone`.
- `GET /reports/summary?telegram_id=&days=` — сводка за последние N дней.
