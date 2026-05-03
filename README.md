# Meal Mentor

Сервис учёта питания: **веб-приложение** (дашборд, дневник, профиль), **Telegram-бот** и опционально **Streamlit** для демо. Бэкенд на **FastAPI** хранит приёмы пищи и профиль в БД, считает **КБЖУ** по CSV и при необходимости вызывает **OpenAI** для распознавания фото и текста.

## Как устроен продукт сейчас

### Веб-интерфейс (`frontend/`)

После входа (email/пароль или Telegram OAuth) пользователь попадает в оболочку **AppShell**: боковое меню, верхняя шапка, плавающая кнопка «+» на мобильных, модалки **«Добавить приём пищи»** и анализа этикетки.

| Раздел | Назначение |
|--------|------------|
| **Главная (дашборд)** | Приветствие, карточка **«Дневник питания»**: съедено **за сегодня** по данным из БД (`GET /users/me/diary` → `today`) против **дневных целей** из активной цели КБЖУ (`nutrition_target`). После сохранения приёма из модалки дашборд обновляется. |
| **Дневник** | **Обзор питания** — кнопка открывает ту же модалку добавления приёма. **Статистика**: переключатель **Неделя** / **Месяц** (данные из одного запроса снимка дневника). Столбцы — калории по дням; средние ккал и БЖУ считаются как сумма за период, делённая на число **дней с ненулевыми калориями** (не на 7 и не на число дней месяца «вслепую»). **История** — последние 3 приёма. **Текущий вес** — из профиля; дельта за неделю — по взвешиваниям за календарную неделю. **Дневные цели** — факт за сегодня vs цели из БД. |
| **Профиль** (`/onboarding/profile`) | Редактирование профиля, аллергенов, расчёт **дневной цели КБЖУ** (калории, белки, жиры, углеводы; без отображения BMR/TDEE в карточке). |

**Шапка:** по клику на аватар — меню **«Мой профиль»** и **«Выйти»**.

**Добавить приём пищи (модалка):** фото с камеры / загрузка файла / текст → публичные эндпоинты `POST /meals/analyze` или `POST /meals/analyze-text` → при подтверждении сохранение в дневник пользователя с JWT: `POST /users/me/meals/save` (ингредиенты + `source_type`).

**PWA и иконки:** `public/manifest.webmanifest`, иконки в `public/icons/`, favicon в `index.html` — можно установить приложение на домашний экран; тема в манифесте согласована с зелёной палитрой UI.

### Telegram-бот

Фото → анализ → подтверждение → сохранение через сценарии, завязанные на `telegram_id`. Текст при низкой уверенности — как раньше. Сводки отчётов — через существующие отчётные эндпоинты.

### Ядро и данные

- Расчёт и хранение **целей КБЖУ** (в т.ч. Миффлин–Сан Жеор): `app/services/nutrition_targets.py`, активная цель привязана к пользователю.
- Снимок дневника для веба: `app/services/diary_snapshot.py` — неделя (пн–вс в TZ профиля), **месяц** (все дни текущего месяца), сегодняшние суммы, последние приёмы, вес.
- Анализ блюда без привязки к Telegram: `app/core/use_cases/meal_analysis.py`.

Подробнее об архитектуре слоёв: [docs/architecture.md](docs/architecture.md).

## Структура репозитория

```
meal-mentor/
├── frontend/                 # React + Vite + TypeScript + Tailwind (основной UI)
│   ├── public/               # PWA manifest, sw.js, иконки, favicon
│   └── src/
│       ├── pages/            # Dashboard, Diary, Profile onboarding, Login…
│       ├── components/layout/# AppShell, AppTopBar, навигация, AddMealModal
│       ├── api/              # authApi, diaryApi, mealsApi
│       └── utils/mealFlow.ts # парсинг ответа анализа (не в каталоге lib/ — см. .gitignore)
├── app/
│   ├── core/                 # use cases (анализ приёма и т.д.)
│   ├── infrastructure/       # OpenAI, nutrition CSV
│   ├── interfaces/         # FastAPI (api/), Telegram, заготовки
│   ├── routers/            # auth.py, users.py (веб JWT: /users/me/…)
│   ├── services/           # diary_snapshot, nutrition_targets, отчёты…
│   ├── db/                 # модели, репозиторий, сессия
│   └── main.py
├── docs/
├── alembic/
├── data/                     # nutrition.csv, промпты
├── service.py                # uvicorn: service:app
├── ui.py                     # Streamlit (демо)
├── requirements.txt
└── README.md
```

## Переменные окружения (бэкенд)

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | OpenAI (vision / текст) для анализа еды и этикеток |
| `PROMPT_PATH`, `PROMPT2_PATH` | Промпты для фото и текста (по умолчанию `./data/promt.txt`, `promt2.txt`) |
| `LOW_CONFIDENCE_THRESHOLD` | Порог уверенности 0–1; ниже — запрос текстового описания (по умолчанию `0.5`) |
| `NUTRITION_CSV_PATH` | CSV нутриентов на 100 г (по умолчанию `./data/nutrition.csv`) |
| `NUTRITION_ENABLE_SEMANTIC` | Семантический поиск (часто тяжёлый на Railway); по умолчанию выкл. |
| `TELEGRAM_BOT_TOKEN`, `BASE_URL` | Для Telegram-бота |
| `DATABASE_URL` | БД (по умолчанию SQLite `sqlite:///./meal_mentor.db`) |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | JWT для веба |

Фронтенд: **`VITE_API_URL`** — базовый URL API (см. `frontend/.env.example`).

## Запуск

### Бэкенд

```bash
pip install -r requirements.txt
uvicorn service:app --reload
```

### Фронтенд

```bash
cd frontend
cp .env.example .env   # задать VITE_API_URL
npm install
npm run dev            # разработка
npm run build          # прод-сборка
```

### Прочее

- **Telegram-бот:** `python -m app.bot.telegram_bot` (бэкенд должен быть доступен по `BASE_URL`).
- **Streamlit:** `streamlit run ui.py` — демо к `POST /generate_response`.
- **Make:** при наличии цели в Makefile — `make run_app` и т.п.

## Схема БД (кратко)

`users` (профиль, вес, цель, активность, TZ), `meals` + `meal_items` + `meal_item_nutrition`, `nutrition_targets`, `daily_summary`, `recommendations_log`, `user_measurements`, `allergens` и др. Состав и БЖУ по строкам приёма — в нормализованных таблицах, не в одном JSON «логе».

## Миграции (Alembic)

```bash
alembic upgrade head
```

Ревизия `001_normalize` и последующие — см. историю в `alembic/`. На пустой БД часто достаточно `init_db()` при старте приложения.

## API: веб-пользователь (Bearer)

Префикс веб-роутера пользователя: **`/users`** (теги в OpenAPI: users-web).

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/users/me` | Профиль, в т.ч. активная `nutrition_target` |
| `PATCH` | `/users/me/profile` | Обновление профиля; пересчёт целей КБЖУ при полных данных |
| `GET` | `/users/me/nutrition-target` | Активная дневная цель КБЖУ |
| `GET` | `/users/me/diary` | Снимок дневника: `week`, `month`, `today`, `recent_meals`, `weight` |
| `POST` | `/users/me/meals/save` | Сохранить приём в дневник (ингредиенты после анализа) |
| `POST` | `/users/me/analyze-label` | Анализ фото этикетки (multipart) |

Аутентификация: **`/auth/register`**, **`/auth/login`**, **`/auth/refresh`**, **`/auth/logout`**, OAuth Telegram — **`/auth/telegram/callback`** и др. (см. `app/routers/auth.py`).

## API: анализ без записи (как у бота и модалки)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/meals/analyze` | `{ "image_base64" }` — состав и БЖУ |
| `POST` | `/meals/analyze-text` | `{ "text" }` — разбор описания |
| `POST` | `/meals/save` | Сохранение по **telegram_id** (бот) |
| `POST` | `/generate_response` | Legacy для Streamlit: `{ "image_base64" }` |

## Документация

- [docs/architecture.md](docs/architecture.md) — слои и потоки.
- [frontend/README.md](frontend/README.md) — кратко про фронт и `VITE_API_URL`.
