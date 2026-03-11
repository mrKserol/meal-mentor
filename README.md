# Meal Mentor

Трекер калорий и состава еды по фото: FastAPI-бэкенд, Telegram-бот и Streamlit для демо/админки.

## Структура проекта

```
meal-mentor/
├── app/
│   ├── api/           # Эндпоинты: users, meals, reports
│   ├── bot/           # Telegram-бот и обработчики (start, photo, report)
│   ├── core/          # config, промпты для vision
│   ├── db/            # Модели, сессия, репозиторий
│   ├── services/      # openai_vision, nutrition, meal, recommendation, report
│   └── main.py        # FastAPI-приложение
├── nutrition.csv      # Опционально: нутриенты на 100 г
├── promt.txt          # Промпт для распознавания состава и веса
├── service.py         # Точка входа для uvicorn service:app
├── ui.py              # Streamlit (демо/админ), не основной клиент
├── assistant.py       # Оставлен для совместимости; логика в app/services/openai_vision.py
├── search.py          # Оставлен для совместимости; логика в app/services/nutrition_service.py
├── .env
├── requirements.txt
└── README.md
```

## Как работает

- **Telegram:** пользователь отправляет фото еды → бот скачивает файл → переводит в base64 → вызывает бэкенд `POST /meals/log` → распознавание (OpenAI Vision) + при наличии CSV расчёт БЖУ/калорий → запись в БД → ответ пользователю; `/report [дней]` — сводка за период.
- **Streamlit (ui.py):** демо/админ: загрузка фото → запрос к `POST /generate_response` → вывод состава, веса и при наличии CSV — диаграмма БЖУ.

## Переменные окружения

- `OPENAI_API_KEY` — ключ OpenAI (обязательно для vision).
- `NUTRITION_CSV_PATH` — путь к CSV с нутриентами на 100 г (колонки: `name`, `calories`, `total_fat`, `protein`, `carbohydrate`). Необязательно.
- `TELEGRAM_BOT_TOKEN` — токен бота (для запуска бота).
- `BASE_URL` — URL бэкенда (по умолчанию `http://127.0.0.1:8000`). Нужен боту для вызова API.
- `DATABASE_URL` — БД (по умолчанию `sqlite:///./meal_mentor.db`).

## Запуск

1. Установка: `pip install -r requirements.txt`
2. Бэкенд: `uvicorn service:app --reload` или `uvicorn app.main:app --reload`
3. Telegram-бот: `python -m app.bot.telegram_bot` (предварительно запустить бэкенд)
4. Streamlit (демо): `streamlit run ui.py`

Можно по-прежнему использовать `make run_app` (бэкенд + Streamlit).

## API

- `POST /generate_response` — тело `{ "image_base64": "..." }` — состав и вес, при наличии CSV — поле `nutrition` (для ui.py).
- `POST /meals/analyze` — то же по полю `image_base64`.
- `POST /meals/log` — тело `{ "telegram_id", "username?", "image_base64", "telegram_file_id?" }` — анализ + запись приёма пищи в дневник (используется ботом).
- `POST /users/register` — регистрация по `telegram_id` / `username`.
- `GET /reports/summary?telegram_id=&days=` — сводка за последние N дней.
