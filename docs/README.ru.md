# Meal Mentor — документация (RU)

[English](README.en.md) · [Корневой README](../README.md) · [Архитектура](architecture.md)

Сервис учёта питания: **веб-приложение**, **Telegram-бот** и **REST API** на FastAPI. Пользователь ведёт дневник приёмов пищи, видит прогресс по калориям и БЖУ, настраивает цели и (на платных тарифах) расширенные возможности. Администраторы управляют пользователями, тарифами и подписками.

---

## Содержание

1. [Возможности продукта](#возможности-продукта)
2. [Архитектура репозитория](#архитектура-репозитория)
3. [Аутентификация](#аутентификация)
4. [Тарифы, лимиты и entitlements](#тарифы-лимиты-и-entitlements)
5. [Веб-интерфейс](#веб-интерфейс)
6. [Telegram-бот](#telegram-бот)
7. [Админ-панель](#админ-панель)
8. [База данных](#база-данных)
9. [Переменные окружения](#переменные-окружения)
10. [Запуск и деплой](#запуск-и-деплой)
11. [Миграции и скрипты](#миграции-и-скрипты)
12. [API](#api)
13. [Тесты](#тесты)

---

## Возможности продукта

### Веб

- **Вход:** email/пароль, **Telegram OAuth**, **Яндекс OAuth** (профиль: email, имя, пол и дата рождения при наличии прав в OAuth-приложении).
- **Дашборд:** приветствие, карточка дневника — факт за сегодня vs дневные цели КБЖУ из БД.
- **Дневник:** статистика за неделю/месяц, история приёмов, вес, дневные цели; добавление приёма за любой выбранный день (включая прошлые и завтра).
- **Профиль:** пол, возраст, рост, вес, цель, активность, аллергены (если включено тарифом), пересчёт целей КБЖУ (Миффлин–Сан Жеор).
- **Добавить приём пищи:** фото / файл / текст → AI-анализ → подтверждение состава и весов → сохранение; редактирование названия и ингредиентов, пересчёт БЖУ без повторного AI.

**Оценка веса (vision):** модель может завышать граммы для одиночных сладостей и лёгкой выпечки (например, один небольшой пряник как 200 г). В `data/promt.txt` / `promt2.txt` заданы типичные веса порции (печенье, пряник, пончик, маффин). Масштабирование веса в коде `NutritionService` не применяется — проблема в оценке LLM, не в расчёте КБЖУ на 100 г. *TODO:* калибровка / лимиты по категориям для single-item.
- **Анализ этикетки:** загрузка фото состава продукта (отдельный промпт).
- **PWA:** установка на домашний экран (`manifest`, service worker, иконки).

### Telegram

- Фото → анализ → подтверждение → сохранение по `telegram_id`.
- Текст при низкой уверенности распознавания.
- Отчёты и сценарии, завязанные на существующие report-эндпоинты.

### Ядро данных

- Нормализованное хранение приёмов: `meals` → `meal_items` → `meal_item_nutrition`.
- Активная **цель КБЖУ** на пользователя (`nutrition_targets`).
- Снимок дневника для UI: `diary_snapshot` (неделя, месяц, сегодня, последние приёмы, вес).
- Матчинг ингредиентов к CSV с алиасами, состоянием (dry/cooked/fried), категориями и регрессионными фикстурами.

---

## Архитектура репозитория

```
meal-mentor/
├── frontend/                 # React + Vite + TypeScript + Tailwind (основной UI)
│   ├── public/               # PWA, иконки, favicon
│   └── src/
│       ├── pages/            # Login, Dashboard, Diary, Profile, Admin, OAuth callbacks
│       ├── components/       # AppShell, AddMealModal, EditMealModal, admin UI
│       ├── api/              # authApi, diaryApi, mealsApi, adminApi
│       └── admin/            # пресеты feature keys для тарифов
├── app/
│   ├── core/                 # use cases (meal_analysis, …)
│   ├── infrastructure/       # OpenAI, nutrition CSV, storage
│   ├── interfaces/
│   │   ├── api/              # /users, /meals, /reports, /subscriptions (бот)
│   │   └── telegram/         # long-polling бот
│   ├── routers/
│   │   ├── auth.py           # JWT, OAuth
│   │   ├── users.py          # /users/me/* (веб JWT)
│   │   └── admin.py          # /admin/* (роль admin)
│   ├── services/             # diary_snapshot, nutrition_targets, feature_access, usage_limits
│   ├── auth/                 # JWT, OAuth providers
│   └── db/                   # models, repository, session
├── alembic/                  # миграции БД
├── data/                     # nutrition.csv, food_aliases.json, промпты
├── scripts/                  # backfill_auth_identities.py и др.
├── tests/                    # nutrition matching, usage limits, …
├── docs/
├── service.py                # uvicorn entry: service:app
└── requirements.txt
```

Подробнее о слоях: [architecture.md](architecture.md).

---

## Аутентификация

- **JWT:** `access_token` + `refresh_token`; в payload — внутренний `users.id` (не меняется при привязке OAuth).
- **Универсальные привязки:** таблица `user_auth_identities` (`provider`, `provider_user_id`). Старые пользователи Telegram по-прежнему имеют `users.telegram_id`; при входе создаётся/находится identity `telegram`.
- **Провайдеры веб-входа:** Telegram OIDC, Яндекс OAuth.
- **Регистрация:** email + пароль с заполнением профиля.

Backfill для существующих Telegram-пользователей:

```bash
python -m scripts.backfill_auth_identities
```

---

## Тарифы, лимиты и entitlements

### Модели

- `plans` + `plan_features` — тариф и набор возможностей (boolean / limit).
- `subscriptions` — активная подписка пользователя на план.
- `user_feature_overrides` — ручные переопределения (админка).
- `feature_usage` — счётчики использования AI (daily / monthly периоды).

### Типы feature keys

| Boolean | Limit |
|---------|-------|
| `nutrition_diary_enabled` | `daily_ai_requests_limit` |
| `advanced_nutrients_enabled` | `daily_ai_chat_messages_limit` |
| `food_photo_recognition_enabled` | `daily_photo_recognition_limit` |
| `label_analysis_enabled` | `monthly_photo_recognition_limit` |
| `ai_chat_enabled` | `monthly_label_analysis_limit` |
| `allergens_enabled` | |

Лимит `-1` — безлимит. Лимит `0` — запрет. Инкремент счётчиков после **успешного** AI-запроса; несколько счётчиков за один запрос — **атомарно** (`increment_many_usage` в `app/services/usage_limits.py`).

### Проверки при веб-AI

- Фото: `food_photo_recognition_enabled` + дневной/месячный лимит фото + общий `daily_ai_requests_limit`.
- Этикетка: `label_analysis_enabled` + `monthly_label_analysis_limit` + дневной AI-лимит.
- Текст без фото: только `daily_ai_requests_limit`.

Эндпоинты с лимитами (JWT): `POST /users/me/meals/analyze`, `analyze-text`, `analyze-image-text`, `POST /users/me/analyze-label`.

Публичные `POST /meals/analyze*` без JWT используются ботом и не учитывают веб-лимиты.

`GET /users/me/entitlements` — текущий план и словарь feature для UI.

Сидинг фич тарифов: миграция `018_seed_plan_features_v2` (планы `free`, `basic_month`, `pro_month`).

---

## Веб-интерфейс

| Маршрут | Страница |
|---------|----------|
| `/login` | Вход (Telegram / Яндекс) |
| `/register` | Регистрация |
| `/auth/telegram/callback`, `/auth/yandex/callback` | OAuth callbacks |
| `/dashboard` | Главная |
| `/diary` | Дневник |
| `/onboarding/profile` | Профиль и цели КБЖУ |
| `/admin` | Админка (роль `admin`) |

**AppShell:** боковое меню, шапка, FAB «+» на мобильных, модалки добавления/редактирования приёма и анализа этикетки.

**Добавить приём:** `POST /users/me/meals/analyze*` → подтверждение → `POST /users/me/meals/save` (опционально `meal_local_date` для прошлого дня).

**Редактирование приёма:** `PATCH /users/me/meals/{id}`, удаление — `DELETE`.

---

## Telegram-бот

```bash
python -m app.bot.telegram_bot
```

Требуется `TELEGRAM_BOT_TOKEN` и доступный API по `BASE_URL`. Бот вызывает публичные эндпоинты `/meals/*` и сохраняет по `telegram_id`.

---

## Админ-панель

Доступ: пользователь с `role=admin` (можно задать через `ADMIN_BOOTSTRAP_EMAILS` при первом входе по email).

Разделы:

- **Пользователи** — поиск, provider (из identities), роль, статус, подписка; свайп влево → удаление с подтверждением; выдача подписки; feature overrides.
- **Тарифы** — создание/редактирование планов и features (boolean/limit с подписями на русском); удаление тарифа (если есть подписки — деактивация).
- **Подписки** — список и отмена.

API: префикс `/admin`, Bearer JWT админа.

---

## База данных

Основные таблицы:

| Таблица | Назначение |
|---------|------------|
| `users` | Профиль, роль, статус, `telegram_id` (legacy, не удалять) |
| `user_auth_identities` | OAuth / telegram / email привязки |
| `meals`, `meal_items`, `meal_item_nutrition` | Приёмы пищи и БЖУ |
| `nutrition_targets` | Дневные цели КБЖУ |
| `allergens` | Аллергены пользователя |
| `user_measurements` | Вес и замеры |
| `plans`, `plan_features` | Тарифы |
| `subscriptions` | Подписки |
| `user_feature_overrides` | Ручные права |
| `feature_usage` | Счётчики AI-лимитов |
| `refresh_tokens` | JWT refresh |
| `daily_summary`, `recommendations_log` | Сводки / рекомендации |

По умолчанию SQLite (`DATABASE_URL`); для продакшена — PostgreSQL.

---

## Переменные окружения

### Backend (`.env.example`)

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | OpenAI для фото/текста/этикеток |
| `PROMPT_PATH`, `PROMPT2_PATH` | Промпты (`data/promt.txt`, `promt2.txt`) |
| `NUTRITION_CSV_PATH`, `FOOD_ALIASES_PATH` | База нутриентов и алиасы |
| `LOW_CONFIDENCE_THRESHOLD` | Порог уверенности для запроса текста (по умолчанию `0.5`) |
| `NUTRITION_DEBUG_MATCHING` | Подробные логи матчинга (`1` / `true`) |
| `NUTRITION_ENABLE_SEMANTIC` | Семантический поиск (тяжёлый; по умолчанию выкл.) |
| `DATABASE_URL` | Строка подключения SQLAlchemy |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM` | JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Сроки токенов |
| `TELEGRAM_BOT_TOKEN`, `BASE_URL` | Бот |
| `TELEGRAM_CLIENT_ID`, `TELEGRAM_CLIENT_SECRET`, `TELEGRAM_REDIRECT_URI` | Telegram OAuth (backend) |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI` | Яндекс OAuth (backend) |
| `ADMIN_BOOTSTRAP_EMAILS` | Email через запятую → admin при входе |
| `MEAL_PHOTO_UPLOAD_DIR` | Каталог фото приёмов на диске |
| `SUBSCRIPTION_DEMO_AUTO` | Демо-активация подписки без оплаты |

### Frontend (`frontend/.env.example`)

| Переменная | Назначение |
|------------|------------|
| `VITE_API_URL` | URL FastAPI |
| `VITE_TELEGRAM_CLIENT_ID`, `VITE_TELEGRAM_REDIRECT_URI` | Telegram OAuth (frontend) |
| `VITE_YANDEX_CLIENT_ID`, `VITE_YANDEX_REDIRECT_URI` | Яндекс OAuth |
| `VITE_YANDEX_SCOPES` | Scopes Яндекса, напр. `login:info login:email login:avatar login:birthday` |

---

## Запуск и деплой

### Backend

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn service:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI: `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev          # http://localhost:5173
npm run build        # dist/
npm run preview      # просмотр сборки
```

### Telegram-бот

```bash
python -m app.bot.telegram_bot
```

### Production (кратко)

- API: Railway / Docker + `uvicorn service:app`.
- Frontend: статика из `frontend/dist` (`npm run build`).
- CORS на API настроен на `*` (при необходимости сузить origins).
- Обязательно сменить `JWT_SECRET_KEY` и секреты OAuth.

---

## Миграции и скрипты

```bash
alembic upgrade head
```

Примеры ревизий: `016_user_auth_identities`, `017_feature_usage`, `018_seed_plan_features_v2`.

```bash
python -m scripts.backfill_auth_identities
```

Создаёт `user_auth_identities` для пользователей с `telegram_id` (не меняет `users.id`).

---

## API

### Auth — `/auth`

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/register` | Регистрация |
| POST | `/login` | Email + пароль |
| POST | `/refresh` | Обновление access token |
| POST | `/logout` | Отзыв refresh token |
| POST | `/telegram/callback` | Telegram OAuth (web) |
| POST | `/yandex/callback` | Яндекс OAuth |

### Web user — `/users` (Bearer)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/me` | Профиль + цели + аллергены |
| PATCH | `/me/profile` | Обновление профиля |
| GET | `/me/entitlements` | Тариф и features |
| GET | `/me/diary` | Снимок дневника |
| GET | `/me/meals/day?date=YYYY-MM-DD` | Приёмы за день |
| POST | `/me/meals/analyze` | Анализ фото (лимиты) |
| POST | `/me/meals/analyze-text` | Анализ текста |
| POST | `/me/meals/analyze-image-text` | Фото + коррекция текстом |
| POST | `/me/meals/save` | Сохранить приём |
| PATCH | `/me/meals/{meal_id}` | Изменить состав |
| DELETE | `/me/meals/{meal_id}` | Удалить приём |
| POST | `/me/analyze-label` | Анализ этикетки (multipart) |
| GET/POST | `/me/measurements` | Вес / замеры |
| GET | `/me/nutrition-target` | Активная цель КБЖУ |

### Meals (бот / legacy) — `/meals`

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/analyze` | Фото base64 (без JWT-лимитов) |
| POST | `/analyze-text` | Текст |
| POST | `/analyze-image-text` | Фото + текст |
| POST | `/recalculate` | БЖУ по ингредиентам без AI |
| POST | `/save` | Сохранение по `telegram_id` |

### Admin — `/admin` (Bearer, role admin)

Пользователи, тарифы, features, подписки, overrides — см. OpenAPI или `app/routers/admin.py`.

---

## Тесты

```bash
pytest
```

Отдельно:

```bash
pytest tests/test_nutrition_matching.py
pytest tests/test_usage_limits.py
pytest tests/test_feature_access.py
```

**Nutrition matching:** фикстуры в `tests/fixtures/nutrition_matching_cases.json`. При багах матчинга добавляйте кейсы и гоняйте регрессию. Подробные логи: `NUTRITION_DEBUG_MATCHING=1`.

**Category-aware matching (кокос):** явное разделение coconut water / meat / milk / cream / oil. В flow «фото + текст» текст пользователя важнее распознавания объекта на фото (например, фото кокоса + «кокосовая вода» → coconut water, не мякоть).

**Category-aware matching (zero/diet напитки):** aliases и scoring для `zero_soft_drink` / `soft_drink`. Нормализатор alias keys приводит к одному ключу варианты вроде «Кока-Кола Зеро», «Кока-кола зеро», «кока кола зеро». Zero-напитки не должны матчиться на regular cola, oil/fat; обычная кола — не на diet/low calorie без явного zero/diet/без сахара.

**Category-aware matching (супы):** добавлены категории `soup` / `prepared_soup`. Они защищают распространённые супы от матчинга на dry mix, condensed, powder, sauce, gravy, oil, fat, shortening и dehydrated rows. Примеры: borscht with bread, generic soup with bread, lentil soup, tomato soup, щи / kharcho / rassolnik / solyanka (aliases). Если пользователь называет распространённое блюдо-суп, сначала добавляйте alias + fixture, а не полагайтесь только на fuzzy search.

**Usage limits:** атомарный инкремент нескольких счётчиков за один AI-запрос.

---

## См. также

- [architecture.md](architecture.md) — потоки Telegram / API / core
- [frontend/README.md](../frontend/README.md) — скрипты npm и `VITE_*`
